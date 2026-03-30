# # -*- coding: utf-8 -*-
# from odoo import models, fields
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
#     charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
#     charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)
#     charity_move_id = fields.Many2one('account.move', string='Charity Journal Entry', readonly=True)
#
#     def _process_order(self, order, existing_order):
#         """
#         Intercept charity metadata sent from the frontend before calling super().
#
#         The frontend sends:
#           order['charity_donation_amount']  — e.g. 3.0
#           order['charity_account_id']       — e.g. 1
#
#         The order total already includes the donation (because the JS bumped
#         the line price_unit via setUnitPrice before serialising), so the normal
#         POS accounting entries will naturally cover the full ₹300.
#         We only need to record the ₹3 split separately for the charity ledger
#         and create the charity journal entry at session close.
#         """
#         charity_amount     = float(order.get('charity_donation_amount') or 0.0)
#         charity_account_id = order.get('charity_account_id') or False
#
#         order_id  = super()._process_order(order, existing_order)
#         pos_order = self.browse(order_id)
#
#         if not pos_order.exists():
#             return order_id
#
#         # Fall back to the POS config's default charity account if none sent
#         if not charity_account_id and pos_order.config_id.charity_account_id:
#             charity_account_id = pos_order.config_id.charity_account_id.id
#
#         if charity_amount > 0 and charity_account_id:
#             pos_order.write({
#                 'charity_donation_amount': charity_amount,
#                 'charity_account_id':      charity_account_id,
#             })
#             pos_order._create_charity_donation()
#
#         return order_id
#
#     def _create_charity_donation(self):
#         """
#         Create the donation ledger record (pos.charity.donation).
#
#         Journal entry is deferred to session close so it groups with the
#         rest of the POS closing entries — exactly like standard Odoo POS.
#         """
#         self.ensure_one()
#         if not (self.charity_donation_amount > 0 and self.charity_account_id):
#             return
#         if self.charity_donation_id:
#             return  # already created (re-validation guard)
#         try:
#             donation = self.env['pos.charity.donation'].create({
#                 'charity_account_id': self.charity_account_id.id,
#                 'pos_session_id':     self.session_id.id,
#                 'pos_order_id':       self.id,
#                 'amount':             self.charity_donation_amount,
#                 'cashier_id':         self.user_id.id,
#                 'state':              'confirmed',
#                 'note':               'Donation from POS Order %s' % self.name,
#             })
#             self.charity_donation_id = donation.id
#             _logger.info(
#                 'Charity donation %.2f recorded for order %s (journal entry pending session close)',
#                 self.charity_donation_amount, self.name,
#             )
#         except Exception as e:
#             _logger.error('Failed to create charity donation record: %s', e)
#
#     def _create_charity_journal_entry(self):
#         """
#         Post the charity journal entry at session closing time.
#
#         Accounting split for a ₹300 order with ₹3 charity:
#           ₹297 → handled by the normal POS sales journal entry (product revenue)
#           ₹3   → this entry:
#                    DEBIT  cash/payment account  ₹3   (money physically in the till)
#                    CREDIT charity GL account    ₹3   (designated charity liability)
#         """
#         self.ensure_one()
#         if self.charity_move_id:
#             return  # already posted, skip re-validation
#
#         config = self.config_id
#         if not config.charity_gl_account_id:
#             _logger.info(
#                 'No charity GL account on POS config — skipping journal entry for order %s',
#                 self.name,
#             )
#             return
#
#         try:
#             journal = config.charity_journal_id or config.journal_id
#             if not journal:
#                 _logger.error('No journal found for charity entry on order %s', self.name)
#                 return
#
#             # Debit side: the payment account (cash drawer / card terminal)
#             debit_account = False
#             for payment in self.payment_ids:
#                 pj = payment.payment_method_id.journal_id
#                 if pj:
#                     debit_account = pj.default_account_id or pj.payment_debit_account_id
#                     if debit_account:
#                         break
#             if not debit_account:
#                 debit_account = journal.default_account_id
#             if not debit_account:
#                 _logger.error('Cannot determine debit account for order %s', self.name)
#                 return
#
#             amount   = self.charity_donation_amount
#             currency = self.currency_id or self.env.company.currency_id
#
#             move = self.env['account.move'].create({
#                 'journal_id': journal.id,
#                 'date':       self.date_order.date() if self.date_order else fields.Date.today(),
#                 'ref':        'Charity Donation - %s' % self.name,
#                 'line_ids': [
#                     (0, 0, {
#                         'name':        'Charity Donation - %s' % self.name,
#                         'account_id':  debit_account.id,
#                         'debit':       amount,
#                         'credit':      0.0,
#                         'currency_id': currency.id,
#                     }),
#                     (0, 0, {
#                         'name':        'Charity Donation - %s' % self.name,
#                         'account_id':  config.charity_gl_account_id.id,
#                         'debit':       0.0,
#                         'credit':      amount,
#                         'currency_id': currency.id,
#                     }),
#                 ],
#             })
#             move.action_post()
#             self.charity_move_id = move.id
#             _logger.info(
#                 'Charity journal entry %s (%.2f) posted for order %s',
#                 move.name, amount, self.name,
#             )
#         except Exception as e:
#             _logger.error(
#                 'Failed to create charity journal entry for order %s: %s', self.name, e
#             )
#
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
        POS accounting entries will naturally cover the full amount.
        We only need to record the charity split separately for the charity ledger
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

        The ₹3 charity is already embedded inside the ₹650 sale total.
        The cash drawer physically received ₹650 total — the full amount
        is already recorded by the standard POS cash entry (CSKDT).

        So the charity entry must NOT debit cash again. Instead we reroute
        ₹3 from Product Sales revenue to the Charity GL account:

            DEBIT  400000 Product Sales   ₹3   (reduce revenue by charity portion)
            CREDIT 201002 Charity         ₹3   (record charity liability/payable)

        This keeps the cash account balanced (₹650 in, ₹650 out) and correctly
        shows that ₹3 of the sale belongs to charity, not the business.

        Fallback: if no sales account is found, we use Account Receivable (PoS)
        (101300) as the debit, which is also correct since it offsets the
        receivable that was already cleared by the cash payment.
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

            # ----------------------------------------------------------------
            # Debit side: Product Sales account (400000) — we reduce revenue
            # by the charity portion since that ₹3 is not business income.
            #
            # Resolution priority:
            #   1. Sales account from the order lines (most accurate)
            #   2. POS config's income account
            #   3. Account Receivable (PoS) — 101300 (safe fallback)
            # ----------------------------------------------------------------
            debit_account = False

            # 1. Try to get the sales/income account from the order lines
            for line in self.lines:
                account = (
                    line.product_id.property_account_income_id
                    or line.product_id.categ_id.property_account_income_categ_id
                )
                if account:
                    debit_account = account
                    break

            # 2. Try the POS config income account
            if not debit_account and config.journal_id:
                debit_account = config.journal_id.default_account_id

            # 3. Fallback: Account Receivable (PoS) — offsets the already-cleared receivable
            if not debit_account:
                pos_receivable_account = self.env['account.account'].search([
                    ('code', 'like', '101300'),
                    ('company_id', '=', self.company_id.id),
                ], limit=1)
                if pos_receivable_account:
                    debit_account = pos_receivable_account

            if not debit_account:
                _logger.error(
                    'Cannot determine debit (sales) account for charity entry on order %s',
                    self.name,
                )
                return

            amount   = self.charity_donation_amount
            currency = self.currency_id or self.env.company.currency_id

            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date':       self.date_order.date() if self.date_order else fields.Date.today(),
                'ref':        'Charity Donation - %s' % self.name,
                'line_ids': [
                    # DEBIT: reduce Product Sales revenue by charity amount
                    (0, 0, {
                        'name':        'Charity Donation - %s' % self.name,
                        'account_id':  debit_account.id,
                        'debit':       amount,
                        'credit':      0.0,
                        'currency_id': currency.id,
                    }),
                    # CREDIT: record the charity liability/payable
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
                'Charity journal entry %s (%.2f) posted for order %s | '
                'Dr: %s  Cr: %s',
                move.name, amount, self.name,
                debit_account.code, config.charity_gl_account_id.code,
            )
        except Exception as e:
            _logger.error(
                'Failed to create charity journal entry for order %s: %s', self.name, e
            )