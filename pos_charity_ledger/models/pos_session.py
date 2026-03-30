# # # -*- coding: utf-8 -*-
# # from odoo import models, fields, api
# #
# #
# # class PosSession(models.Model):
# #     _inherit = 'pos.session'
# #
# #     charity_donation_total = fields.Float(
# #         string='Total Charity Donations',
# #         compute='_compute_charity_totals',
# #         store=True,
# #     )
# #     charity_donation_count = fields.Integer(
# #         string='Number of Donations',
# #         compute='_compute_charity_totals',
# #         store=True,
# #     )
# #
# #     @api.depends('order_ids')
# #     def _compute_charity_totals(self):
# #         for session in self:
# #             donations = self.env['pos.charity.donation'].search([
# #                 ('pos_session_id', '=', session.id),
# #                 ('state', '=', 'confirmed'),
# #             ])
# #             session.charity_donation_total = sum(donations.mapped('amount'))
# #             session.charity_donation_count = len(donations)
# #
# #     def _loader_params_pos_config(self):
# #         result = super()._loader_params_pos_config()
# #         result['search_params']['fields'].extend([
# #             'charity_enabled',
# #             'charity_account_id',
# #             'charity_button_label',
# #             'charity_gl_account_id',
# #             'charity_journal_id',
# #         ])
# #         return result
# #
# #     def _pos_ui_models_to_load(self):
# #         result = super()._pos_ui_models_to_load()
# #         result.append('pos.charity.account')
# #         return result
# #
# #     def _loader_params_pos_charity_account(self):
# #         return {
# #             'search_params': {
# #                 'domain': [('active', '=', True)],
# #                 'fields': ['name', 'description'],
# #             }
# #         }
# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# import logging
#
# _logger = logging.getLogger(__name__)
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     charity_donation_total = fields.Float(
#         string='Total Charity Donations',
#         compute='_compute_charity_totals',
#         store=True,
#     )
#     charity_donation_count = fields.Integer(
#         string='Number of Donations',
#         compute='_compute_charity_totals',
#         store=True,
#     )
#
#     @api.depends('order_ids', 'order_ids.charity_donation_amount')
#     def _compute_charity_totals(self):
#         for session in self:
#             orders = session.order_ids.filtered(
#                 lambda o: o.charity_donation_amount > 0
#             )
#             session.charity_donation_total = sum(
#                 orders.mapped('charity_donation_amount')
#             )
#             session.charity_donation_count = len(orders)
#
#     def get_charity_totals(self):
#         """RPC method called by the closing popup to get fresh charity totals.
#         Returns a dict with total and count so the closing register can display
#         the charity donations collected during the session."""
#         self.ensure_one()
#         orders = self.order_ids.filtered(lambda o: o.charity_donation_amount > 0)
#         total = sum(orders.mapped('charity_donation_amount'))
#         count = len(orders)
#         return {
#             'total': total,
#             'count': count,
#         }
#
#     # ------------------------------------------------------------------
#     # Session closing — create charity journal entries here so they
#     # appear together with the rest of the POS session entries, matching
#     # standard Odoo POS behaviour (no entries until register is closed).
#     # ------------------------------------------------------------------
#     def action_pos_session_closing_control(self, balancing_account=False,
#                                            amount_to_balance=0,
#                                            bank_payment_method_diffs=None):
#         result = super().action_pos_session_closing_control(
#             balancing_account=balancing_account,
#             amount_to_balance=amount_to_balance,
#             bank_payment_method_diffs=bank_payment_method_diffs,
#         )
#         self._create_pending_charity_journal_entries()
#         return result
#
#     def _create_pending_charity_journal_entries(self):
#         """Post charity journal entries for every order in this session
#         that has a donation amount but no journal entry yet."""
#         for session in self:
#             orders = session.order_ids.filtered(
#                 lambda o: o.charity_donation_amount > 0
#                 and o.charity_account_id
#                 and not o.charity_move_id
#             )
#             for order in orders:
#                 order._create_charity_journal_entry()
#             if orders:
#                 _logger.info(
#                     'Created charity journal entries for %s order(s) on session %s',
#                     len(orders), session.name,
#                 )
#
#     # ------------------------------------------------------------------
#     # POS UI data loaders
#     # ------------------------------------------------------------------
#     def _loader_params_pos_config(self):
#         result = super()._loader_params_pos_config()
#         result['search_params']['fields'].extend([
#             'charity_enabled',
#             'charity_account_id',
#             'charity_button_label',
#             'charity_gl_account_id',
#             'charity_journal_id',
#         ])
#         return result
#
#     def _pos_ui_models_to_load(self):
#         result = super()._pos_ui_models_to_load()
#         result.append('pos.charity.account')
#         return result
#
#     def _loader_params_pos_charity_account(self):
#         return {
#             'search_params': {
#                 'domain': [('active', '=', True)],
#                 'fields': ['name', 'description'],
#             }
#         }
# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    charity_donation_total = fields.Float(
        string='Total Charity Donations',
        compute='_compute_charity_totals',
        store=False,   # NOT stored — avoids cross-model @depends resolution at boot
    )
    charity_donation_count = fields.Integer(
        string='Number of Donations',
        compute='_compute_charity_totals',
        store=False,
    )

    @api.depends('order_ids')
    def _compute_charity_totals(self):
        """
        Compute charity totals from pos.charity.donation records.
        We read from pos.charity.donation (not directly from pos.order fields)
        to avoid cross-model dependency issues at module load time.
        """
        for session in self:
            donations = self.env['pos.charity.donation'].search([
                ('pos_session_id', '=', session.id),
                ('state', '=', 'confirmed'),
            ])
            session.charity_donation_total = sum(donations.mapped('amount'))
            session.charity_donation_count = len(donations)

    def get_charity_totals(self):
        """
        RPC method called by the closing popup to get fresh charity totals.
        Returns total and count of charity donations in this session.
        """
        self.ensure_one()
        donations = self.env['pos.charity.donation'].search([
            ('pos_session_id', '=', self.id),
            ('state', '=', 'confirmed'),
        ])
        return {
            'total': sum(donations.mapped('amount')),
            'count': len(donations),
        }

    # ------------------------------------------------------------------
    # Session closing — post charity journal entries here, together with
    # all other POS closing entries.  This is the ONLY place our charity
    # entries are ever created.
    # ------------------------------------------------------------------
    def action_pos_session_closing_control(self, balancing_account=False,
                                           amount_to_balance=0,
                                           bank_payment_method_diffs=None):
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