# # # -*- coding: utf-8 -*-
# # import logging
# # from odoo import api, models
# #
# # _logger = logging.getLogger(__name__)
# #
# # _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
# #
# #
# # def _get_user_warehouse(user):
# #     for fname in _WAREHOUSE_FIELDS:
# #         if fname in user._fields:
# #             return getattr(user, fname, False)
# #     return False
# #
# #
# # class AccountMove(models.Model):
# #     _inherit = 'account.move'
# #
# #     def _get_warehouse_analytic_account(self):
# #         wh = _get_user_warehouse(self.env.user)
# #         if wh and wh.analytic_account_id:
# #             return wh.analytic_account_id
# #         return False
# #
# #     def _apply_warehouse_analytic_to_lines(self):
# #         """
# #         Stamp warehouse analytic on ALL invoice lines AND journal entry lines
# #         so every entry is fully tagged for branch-level reporting.
# #         Covers vendor bills, customer invoices, credit notes and refunds.
# #         """
# #         analytic_account = self._get_warehouse_analytic_account()
# #         if not analytic_account:
# #             return
# #
# #         key = str(analytic_account.id)
# #         for move in self:
# #             if move.move_type not in (
# #                 'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
# #             ):
# #                 continue
# #
# #             # Apply to invoice lines (visible in Invoice Lines tab)
# #             for line in move.invoice_line_ids.filtered(
# #                 lambda l: l.account_id and not l.display_type
# #             ):
# #                 existing = line.analytic_distribution or {}
# #                 if key not in existing:
# #                     new_dist = dict(existing)
# #                     new_dist[key] = 100.0
# #                     line.analytic_distribution = new_dist
# #
# #             # Also apply to ALL journal entry lines (visible in Journal Items tab)
# #             # This includes receivable, payable, tax lines — for full branch visibility
# #             for line in move.line_ids.filtered(
# #                 lambda l: l.account_id and not l.display_type
# #             ):
# #                 existing = line.analytic_distribution or {}
# #                 if key not in existing:
# #                     new_dist = dict(existing)
# #                     new_dist[key] = 100.0
# #                     line.analytic_distribution = new_dist
# #                     _logger.debug(
# #                         'Warehouse analytic %s applied to journal line %s (%s)',
# #                         analytic_account.name, line.id, line.account_id.code,
# #                     )
# #
# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         moves = super().create(vals_list)
# #         moves._apply_warehouse_analytic_to_lines()
# #         return moves
# #
# #     def write(self, vals):
# #         result = super().write(vals)
# #         if any(k in vals for k in ('invoice_line_ids', 'line_ids', 'state', 'move_type')):
# #             self._apply_warehouse_analytic_to_lines()
# #         return result
# #
# #     def action_post(self):
# #         self._apply_warehouse_analytic_to_lines()
# #         return super().action_post()
# #
# #
# # class AccountMoveLine(models.Model):
# #     _inherit = 'account.move.line'
# #
# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         lines = super().create(vals_list)
# #         lines.move_id._apply_warehouse_analytic_to_lines()
# #         return lines
# #
# #     def write(self, vals):
# #         result = super().write(vals)
# #         if any(k in vals for k in ('account_id', 'product_id')):
# #             self.move_id._apply_warehouse_analytic_to_lines()
# #         return result
# #
# #     @api.onchange('product_id', 'account_id')
# #     def _onchange_product_apply_warehouse_analytic(self):
# #         if not self.move_id or self.move_id.move_type not in (
# #             'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
# #         ):
# #             return
# #         wh = _get_user_warehouse(self.env.user)
# #         if not wh or not wh.analytic_account_id:
# #             return
# #         key = str(wh.analytic_account_id.id)
# #         existing = self.analytic_distribution or {}
# #         if key not in existing:
# #             new_dist = dict(existing)
# #             new_dist[key] = 100.0
# #             self.analytic_distribution = new_dist
#
# # -*- coding: utf-8 -*-
# import logging
# from odoo import api, models
#
# _logger = logging.getLogger(__name__)
#
# _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
#
#
# def _get_user_warehouse(user):
#     for fname in _WAREHOUSE_FIELDS:
#         if fname in user._fields:
#             return getattr(user, fname, False)
#     return False
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     def _get_warehouse_analytic_account(self):
#         wh = _get_user_warehouse(self.env.user)
#         if wh and wh.analytic_account_id:
#             return wh.analytic_account_id
#         return False
#
#     def _apply_warehouse_analytic_to_lines(self):
#         """
#         Stamp warehouse analytic on ALL invoice lines AND journal entry lines
#         so every entry is fully tagged for branch-level reporting.
#         Covers vendor bills, customer invoices, credit notes and refunds.
#         """
#         analytic_account = self._get_warehouse_analytic_account()
#         if not analytic_account:
#             return
#
#         key = str(analytic_account.id)
#         for move in self:
#             if move.move_type not in (
#                 'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
#             ):
#                 continue
#
#             # Apply to invoice lines (visible in Invoice Lines tab)
#             for line in move.invoice_line_ids.filtered(
#                 lambda l: l.account_id and not l.display_type
#             ):
#                 existing = line.analytic_distribution or {}
#                 if key not in existing:
#                     new_dist = dict(existing)
#                     new_dist[key] = 100.0
#                     line.analytic_distribution = new_dist
#
#             # Also apply to ALL journal entry lines (visible in Journal Items tab)
#             # This includes receivable, payable, tax lines — for full branch visibility
#             for line in move.line_ids.filtered(
#                 lambda l: l.account_id and not l.display_type
#             ):
#                 existing = line.analytic_distribution or {}
#                 if key not in existing:
#                     new_dist = dict(existing)
#                     new_dist[key] = 100.0
#                     line.analytic_distribution = new_dist
#                     _logger.debug(
#                         'Warehouse analytic %s applied to journal line %s (%s)',
#                         analytic_account.name, line.id, line.account_id.code,
#                     )
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         moves = super().create(vals_list)
#         moves._apply_warehouse_analytic_to_lines()
#         return moves
#
#     def write(self, vals):
#         result = super().write(vals)
#         if any(k in vals for k in ('invoice_line_ids', 'line_ids', 'state', 'move_type')):
#             self._apply_warehouse_analytic_to_lines()
#         return result
#
#     def action_post(self):
#         self._apply_warehouse_analytic_to_lines()
#         return super().action_post()
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     def _get_stock_input_account(self):
#         """
#         Return the Stock Interim (Received) account from the product's
#         category if this line is on a vendor bill with a storable product.
#         Returns False otherwise.
#         """
#         if (
#             self.move_id.move_type == 'in_invoice'
#             and self.product_id
#             and self.product_id.type == 'consu'
#             and self.display_type == 'product'
#             and self.product_id.categ_id.property_stock_account_input_categ_id
#         ):
#             return self.product_id.categ_id.property_stock_account_input_categ_id
#         return False
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         lines = super().create(vals_list)
#         # Auto-set stock interim account on vendor bill lines
#         for line in lines:
#             stock_account = line._get_stock_input_account()
#             if stock_account and line.account_id != stock_account:
#                 line.account_id = stock_account
#         lines.move_id._apply_warehouse_analytic_to_lines()
#         return lines
#
#     def write(self, vals):
#         result = super().write(vals)
#         if any(k in vals for k in ('account_id', 'product_id')):
#             self.move_id._apply_warehouse_analytic_to_lines()
#         return result
#
#     @api.onchange('product_id', 'account_id')
#     def _onchange_product_apply_warehouse_analytic(self):
#         if not self.move_id or self.move_id.move_type not in (
#             'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
#         ):
#             return
#         # Auto-set stock interim account when product is selected on vendor bill
#         stock_account = self._get_stock_input_account()
#         if stock_account and self.account_id != stock_account:
#             self.account_id = stock_account
#         # Apply warehouse analytic
#         wh = _get_user_warehouse(self.env.user)
#         if not wh or not wh.analytic_account_id:
#             return
#         key = str(wh.analytic_account_id.id)
#         existing = self.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             self.analytic_distribution = new_dist
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


def _is_pos_move(move):
    """
    Return True if this move was generated by POS.

    POS moves must be skipped in account_move.py — they are handled by
    pos_order.py using the POS config's warehouse (not the user's warehouse).

    Detection strategies (any one is sufficient):
      A. Move name starts with POSS/ or POSJ/
      B. Move has pos_order_ids (invoice created from POS action_pos_order_invoice)
      C. Move's journal is used by any POS payment method
         (catches CRDCH/, CSCHL/, CSH2/ payment journal entries)
    """
    name = move.name or ''

    # A. Name prefix
    if name.startswith(('POSS/', 'POSJ/')):
        return True

    # B. Linked POS orders
    if hasattr(move, 'pos_order_ids') and move.pos_order_ids:
        _logger.debug('Skipping POS invoice %s (has pos_order_ids)', name)
        return True

    # C. Journal belongs to a POS payment method
    journal = move.journal_id
    if journal:
        pm_exists = move.env['pos.payment.method'].search([
            ('journal_id', '=', journal.id),
        ], limit=1)
        if pm_exists:
            return True

    return False


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_warehouse_analytic_account(self):
        wh = _get_user_warehouse(self.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """
        Stamp warehouse analytic (from logged-in user's default warehouse)
        on invoices and bills ONLY.

        Skips all POS-generated moves — those are handled by pos_order.py
        using the correct POS config warehouse analytic.
        """
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return

        key = str(analytic_account.id)

        for move in self:
            if move.move_type not in (
                'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
            ):
                continue

            # ── CRITICAL: skip all POS-generated moves ──────────────────────
            if _is_pos_move(move):
                _logger.debug(
                    'account_move: skipping POS move %s (journal=%s)',
                    move.name, move.journal_id.name,
                )
                continue
            # ────────────────────────────────────────────────────────────────

            lines_to_tag = move.line_ids.filtered(
                lambda l: l.account_id
                and l.display_type not in ('line_section', 'line_note')
            )

            for line in lines_to_tag:
                existing = line.analytic_distribution or {}
                if key not in existing:
                    new_dist = dict(existing)
                    new_dist[key] = 100.0
                    try:
                        line.sudo().with_context(
                            check_move_validity=False,
                            skip_account_move_synchronization=True,
                        ).analytic_distribution = new_dist
                        _logger.debug(
                            'Warehouse analytic %s → %s line %s (%s)',
                            analytic_account.name,
                            move.name or 'draft',
                            line.id,
                            line.account_id.code,
                        )
                    except Exception as e:
                        _logger.warning(
                            'Could not apply analytic to line %s on %s: %s',
                            line.id, move.name, e,
                        )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_warehouse_analytic_to_lines()
        return moves

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ('invoice_line_ids', 'line_ids', 'state', 'move_type')):
            self._apply_warehouse_analytic_to_lines()
        return result

    def action_post(self):
        self._apply_warehouse_analytic_to_lines()
        result = super().action_post()
        # Second pass to catch receivable/payable lines finalized during posting
        self._apply_warehouse_analytic_to_lines()
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_stock_input_account(self):
        if (
            self.move_id.move_type == 'in_invoice'
            and self.product_id
            and self.product_id.type == 'consu'
            and self.display_type == 'product'
            and self.product_id.categ_id.property_stock_account_input_categ_id
        ):
            return self.product_id.categ_id.property_stock_account_input_categ_id
        return False

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            stock_account = line._get_stock_input_account()
            if stock_account and line.account_id != stock_account:
                line.account_id = stock_account
        lines.move_id._apply_warehouse_analytic_to_lines()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ('account_id', 'product_id')):
            self.move_id._apply_warehouse_analytic_to_lines()
        return result

    @api.onchange('product_id', 'account_id')
    def _onchange_product_apply_warehouse_analytic(self):
        if not self.move_id or self.move_id.move_type not in (
            'in_invoice', 'in_refund', 'out_invoice', 'out_refund'
        ):
            return
        if _is_pos_move(self.move_id):
            return
        stock_account = self._get_stock_input_account()
        if stock_account and self.account_id != stock_account:
            self.account_id = stock_account
        wh = _get_user_warehouse(self.env.user)
        if not wh or not wh.analytic_account_id:
            return
        key = str(wh.analytic_account_id.id)
        existing = self.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            self.analytic_distribution = new_dist