# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
<<<<<<< HEAD
    charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
    charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)

    def _create_charity_donation(self):
        self.ensure_one()
        if self.charity_donation_amount > 0 and self.charity_account_id:
            try:
                donation = self.env['pos.charity.donation'].create({
                    'charity_account_id': self.charity_account_id.id,
                    'pos_session_id': self.session_id.id,
                    'pos_order_id': self.id,
                    'amount': self.charity_donation_amount,
                    'cashier_id': self.user_id.id,
                    'state': 'confirmed',
                    'note': f'Donation from POS Order {self.name}',
                })
                self.charity_donation_id = donation.id
                _logger.info('Charity donation of %s created for order %s',
                             self.charity_donation_amount, self.name)
            except Exception as e:
                _logger.error('Failed to create charity donation: %s', str(e))
=======
    charity_account_id = fields.Many2one(
        'pos.charity.account', string='Charity Account')
    charity_donation_id = fields.Many2one(
        'pos.charity.donation', string='Donation Record', readonly=True)
    charity_move_id = fields.Many2one(
        'account.move', string='Charity Journal Entry', readonly=True)

    def _process_order(self, order, existing_order):
        """Odoo 19: _process_order(self, order, existing_order)"""
        # Extract charity data BEFORE calling super (super may pop keys)
        charity_amount = order.get('charity_donation_amount', 0.0) or 0.0
        charity_account_id = order.get('charity_account_id', False)

        order_id = super()._process_order(order, existing_order)

        if charity_amount > 0 and charity_account_id:
            pos_order = self.browse(order_id)
            if pos_order.exists():
                pos_order.write({
                    'charity_donation_amount': charity_amount,
                    'charity_account_id': charity_account_id,
                })
                pos_order._create_charity_donation()
>>>>>>> b8cb2dc (custom)

    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        charity_amount = order.get('charity_donation_amount', 0.0)
        charity_account_id = order.get('charity_account_id', False)
        if charity_amount and charity_amount > 0 and charity_account_id:
            pos_order = self.browse(order_id)
            if pos_order.exists():
                pos_order.write({
                    'charity_donation_amount': charity_amount,
                    'charity_account_id': charity_account_id,
                })
                pos_order._create_charity_donation()
        return order_id
<<<<<<< HEAD
=======

    def _create_charity_donation(self):
        """Create charity donation ledger record and journal entry."""
        self.ensure_one()
        if not (self.charity_donation_amount > 0 and self.charity_account_id):
            return

        # Create donation record
        try:
            donation = self.env['pos.charity.donation'].create({
                'charity_account_id': self.charity_account_id.id,
                'pos_session_id': self.session_id.id,
                'pos_order_id': self.id,
                'amount': self.charity_donation_amount,
                'cashier_id': self.user_id.id,
                'state': 'confirmed',
                'note': f'Donation from POS Order {self.name}',
            })
            self.charity_donation_id = donation.id
            _logger.info('Charity donation of %s created for order %s',
                         self.charity_donation_amount, self.name)
        except Exception as e:
            _logger.error('Failed to create charity donation record: %s', str(e))
            return

        # Create journal entry if GL account is configured
        self._create_charity_journal_entry()

    def _create_charity_journal_entry(self):
        """Create accounting journal entry for charity donation."""
        self.ensure_one()
        config = self.config_id

        # Check if GL account is configured
        if not config.charity_gl_account_id:
            _logger.info(
                'No charity GL account configured for POS %s, skipping journal entry',
                config.name
            )
            return

        try:
            # Determine journal to use
            journal = config.charity_journal_id or config.journal_id
            if not journal:
                _logger.error('No journal found for charity entry on order %s', self.name)
                return

            # Determine debit account (cash/payment account from the POS payment method)
            debit_account = False
            for payment in self.payment_ids:
                if payment.payment_method_id and payment.payment_method_id.journal_id:
                    pj = payment.payment_method_id.journal_id
                    debit_account = (
                        pj.default_account_id or
                        pj.payment_debit_account_id
                    )
                    if debit_account:
                        break

            if not debit_account:
                # Fallback: use journal's default account
                debit_account = journal.default_account_id

            if not debit_account:
                _logger.error(
                    'Could not determine debit account for charity entry on order %s',
                    self.name
                )
                return

            credit_account = config.charity_gl_account_id
            amount = self.charity_donation_amount
            currency = self.currency_id or self.env.company.currency_id

            move_vals = {
                'journal_id': journal.id,
                'date': self.date_order.date() if self.date_order else fields.Date.today(),
                'ref': _('Charity Donation - %s') % self.name,
                'line_ids': [
                    # Debit: Cash/Bank (money received and kept)
                    (0, 0, {
                        'name': _('Charity Donation - %s') % self.name,
                        'account_id': debit_account.id,
                        'debit': amount,
                        'credit': 0.0,
                        'currency_id': currency.id,
                    }),
                    # Credit: Charity Account (liability/income)
                    (0, 0, {
                        'name': _('Charity Donation - %s') % self.name,
                        'account_id': credit_account.id,
                        'debit': 0.0,
                        'credit': amount,
                        'currency_id': currency.id,
                    }),
                ],
            }

            move = self.env['account.move'].create(move_vals)
            move.action_post()  # Post/validate the journal entry
            self.charity_move_id = move.id

            # Link to donation record too
            if self.charity_donation_id:
                self.charity_donation_id.write({
                    'note': f'Donation from {self.name} | Journal Entry: {move.name}'
                })

            _logger.info(
                'Charity journal entry %s created for order %s (amount: %s)',
                move.name, self.name, amount
            )

        except Exception as e:
            _logger.error(
                'Failed to create charity journal entry for order %s: %s',
                self.name, str(e)
            )


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'
    # No changes needed to order lines
    pass
>>>>>>> b8cb2dc (custom)
