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

# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    charity_donation_total = fields.Float(
        string='Total Charity Donations',
        compute='_compute_charity_totals',
        store=True,
    )
    charity_donation_count = fields.Integer(
        string='Number of Donations',
        compute='_compute_charity_totals',
        store=True,
    )

    @api.depends('order_ids', 'order_ids.charity_donation_amount')
    def _compute_charity_totals(self):
        for session in self:
            orders = session.order_ids.filtered(
                lambda o: o.charity_donation_amount > 0
            )
            session.charity_donation_total = sum(
                orders.mapped('charity_donation_amount')
            )
            session.charity_donation_count = len(orders)

    def get_charity_totals(self):
        """
        RPC method called by the closing popup to get fresh charity totals.
        Returns total and count of charity donations in this session.
        """
        self.ensure_one()
        orders = self.order_ids.filtered(lambda o: o.charity_donation_amount > 0)
        return {
            'total': sum(orders.mapped('charity_donation_amount')),
            'count': len(orders),
        }

    # ------------------------------------------------------------------
    # Enforce: charity journal entries post ONLY at Close Register.
    #
    # Odoo 19 CE has a per-POS-config setting called `_journal_entry_type`
    # (or `journal_entry_type`) which controls whether entries are posted
    # per order or at session closing. We enforce the correct value here
    # at session open so the cashier's backend setting cannot override it.
    # ------------------------------------------------------------------
    def _check_pos_session_balance(self):
        """Called at session open. Enforce session-close posting mode."""
        result = super()._check_pos_session_balance()
        # Ensure journal entries post at closing, not per order
        self._enforce_closing_journal_mode()
        return result

    def _enforce_closing_journal_mode(self):
        """
        Set journal_entry_type = 'at_closing' on the POS config if it is
        currently set to post per-order ('at_each_order' or similar).
        This ensures NO journal entries appear in the backend until the
        cashier clicks 'Close Register'.
        """
        for session in self:
            config = session.config_id
            if not config.charity_enabled:
                continue
            # Odoo 19 CE field name variants — try both
            for field_name in ('journal_entry_type', '_journal_entry_type'):
                if hasattr(config, field_name):
                    current = getattr(config, field_name)
                    if current and current != 'at_closing':
                        try:
                            config.write({field_name: 'at_closing'})
                            _logger.info(
                                'POS config "%s": set %s=at_closing for charity module '
                                '(was: %s). Journal entries will only post at Close Register.',
                                config.name, field_name, current,
                            )
                        except Exception as e:
                            _logger.warning(
                                'Could not set %s on POS config "%s": %s',
                                field_name, config.name, e,
                            )
                    break

    # ------------------------------------------------------------------
    # Session closing — post charity journal entries here, together with
    # all other POS closing entries.  This is the ONLY place our charity
    # entries are ever created.
    # ------------------------------------------------------------------
    def action_pos_session_closing_control(self, balancing_account=False,
                                           amount_to_balance=0,
                                           bank_payment_method_diffs=None):
        """
        Standard POS session close.  After super() posts all the normal
        POS accounting entries, we post the charity-specific entries.

        Flow for a ₹297 order with ₹3 charity (total collected ₹300):
          • Normal POS entry  : covers the full ₹300 order total
          • Charity entry     : DEBIT cash ₹3 / CREDIT charity GL ₹3
            (this splits the ₹3 into the designated charity account)
        """
        result = super().action_pos_session_closing_control(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )
        self._create_pending_charity_journal_entries()
        return result

    def _create_pending_charity_journal_entries(self):
        """
        Post charity journal entries for every order in this session that
        has a donation but no charity journal entry yet.
        Safe to call multiple times — skips already-posted orders.
        """
        for session in self:
            orders = session.order_ids.filtered(
                lambda o: o.charity_donation_amount > 0
                and o.charity_account_id
                and not o.charity_move_id
            )
            for order in orders:
                order._create_charity_journal_entry()
            if orders:
                _logger.info(
                    'Posted charity journal entries for %s order(s) on session %s',
                    len(orders), session.name,
                )

    # ------------------------------------------------------------------
    # POS UI data loaders
    # ------------------------------------------------------------------
    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend([
            'charity_enabled',
            'charity_account_id',
            'charity_button_label',
            'charity_gl_account_id',
            'charity_journal_id',
        ])
        return result

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('pos.charity.account')
        return result

    def _loader_params_pos_charity_account(self):
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name', 'description'],
            }
        }