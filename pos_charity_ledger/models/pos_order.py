# -*- coding: utf-8 -*-
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
    charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
    charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)
    charity_move_id = fields.Many2one('account.move', string='Charity Journal Entry', readonly=True)

    def _process_order(self, order, existing_order):
        """
        Intercept charity metadata sent from the frontend before calling super().

        The frontend sends:
          order['charity_donation_amount']  — e.g. 3.0
          order['charity_account_id']       — e.g. 1

        The order total already includes the donation (because the JS bumped
        the line price_unit via setUnitPrice before serialising), so the normal
        POS accounting entries will naturally cover the full ₹300.
        We only need to record the ₹3 split separately for the charity ledger
        and create the charity journal entry at session close.
        """
        charity_amount     = float(order.get('charity_donation_amount') or 0.0)
        charity_account_id = order.get('charity_account_id') or False

        order_id  = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)

        if not pos_order.exists():
            return order_id

        # Fall back to the POS config's default charity account if none sent
        if not charity_account_id and pos_order.config_id.charity_account_id:
            charity_account_id = pos_order.config_id.charity_account_id.id

        if charity_amount > 0 and charity_account_id:
            pos_order.write({
                'charity_donation_amount': charity_amount,
                'charity_account_id':      charity_account_id,
            })
            pos_order._create_charity_donation()

        return order_id

    def _create_charity_donation(self):
        """
        Create the donation ledger record (pos.charity.donation).

        Journal entry is deferred to session close so it groups with the
        rest of the POS closing entries — exactly like standard Odoo POS.
        """
        self.ensure_one()
        if not (self.charity_donation_amount > 0 and self.charity_account_id):
            return
        if self.charity_donation_id:
            return  # already created (re-validation guard)
        try:
            donation = self.env['pos.charity.donation'].create({
                'charity_account_id': self.charity_account_id.id,
                'pos_session_id':     self.session_id.id,
                'pos_order_id':       self.id,
                'amount':             self.charity_donation_amount,
                'cashier_id':         self.user_id.id,
                'state':              'confirmed',
                'note':               'Donation from POS Order %s' % self.name,
            })
            self.charity_donation_id = donation.id
            _logger.info(
                'Charity donation %.2f recorded for order %s (journal entry pending session close)',
                self.charity_donation_amount, self.name,
            )
        except Exception as e:
            _logger.error('Failed to create charity donation record: %s', e)

    def _create_charity_journal_entry(self):
        """
        Post the charity journal entry at session closing time.

        Accounting split for a ₹300 order with ₹3 charity:
          ₹297 → handled by the normal POS sales journal entry (product revenue)
          ₹3   → this entry:
                   DEBIT  cash/payment account  ₹3   (money physically in the till)
                   CREDIT charity GL account    ₹3   (designated charity liability)
        """
        self.ensure_one()
        if self.charity_move_id:
            return  # already posted, skip re-validation

        config = self.config_id
        if not config.charity_gl_account_id:
            _logger.info(
                'No charity GL account on POS config — skipping journal entry for order %s',
                self.name,
            )
            return

        try:
            journal = config.charity_journal_id or config.journal_id
            if not journal:
                _logger.error('No journal found for charity entry on order %s', self.name)
                return

            # Debit side: the payment account (cash drawer / card terminal)
            debit_account = False
            for payment in self.payment_ids:
                pj = payment.payment_method_id.journal_id
                if pj:
                    debit_account = pj.default_account_id or pj.payment_debit_account_id
                    if debit_account:
                        break
            if not debit_account:
                debit_account = journal.default_account_id
            if not debit_account:
                _logger.error('Cannot determine debit account for order %s', self.name)
                return

            amount   = self.charity_donation_amount
            currency = self.currency_id or self.env.company.currency_id

            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date':       self.date_order.date() if self.date_order else fields.Date.today(),
                'ref':        'Charity Donation - %s' % self.name,
                'line_ids': [
                    (0, 0, {
                        'name':        'Charity Donation - %s' % self.name,
                        'account_id':  debit_account.id,
                        'debit':       amount,
                        'credit':      0.0,
                        'currency_id': currency.id,
                    }),
                    (0, 0, {
                        'name':        'Charity Donation - %s' % self.name,
                        'account_id':  config.charity_gl_account_id.id,
                        'debit':       0.0,
                        'credit':      amount,
                        'currency_id': currency.id,
                    }),
                ],
            })
            move.action_post()
            self.charity_move_id = move.id
            _logger.info(
                'Charity journal entry %s (%.2f) posted for order %s',
                move.name, amount, self.name,
            )
        except Exception as e:
            _logger.error(
                'Failed to create charity journal entry for order %s: %s', self.name, e
            )