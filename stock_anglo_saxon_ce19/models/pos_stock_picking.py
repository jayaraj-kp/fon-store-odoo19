# # -*- coding: utf-8 -*-
# """
# pos_stock_picking.py
#
# Hooks into POS order processing to create Anglo-Saxon delivery valuation
# entries (DR 121200 / CR 110100) immediately after a POS picking is completed.
#
# ODOO 19 POS FLOW:
#     sync_from_ui
#       └─ _process_order
#            └─ _process_saved_order
#                 ├─ action_pos_order_paid   (payment/invoice)
#                 └─ _create_order_picking   (picking created HERE, state=done)
#
# WHY NOT _action_done:
#     picking.pos_order_id is NOT reliably set when _action_done fires during
#     POS sync_from_ui, so a skip-check on pos_order_id would miss POS pickings.
#     We hook _process_saved_order instead, which runs AFTER the picking exists
#     and is done.
#
# ANALYTIC RESOLUTION:
#     We resolve analytic from picking_type_id → warehouse_id directly.
#     env.user is unreliable in POS background/session-close context (it resolves
#     to Administrator, which may belong to the wrong warehouse).
#
# _action_done FALLBACK:
#     Still present for non-POS outgoing pickings validated programmatically
#     (schedulers, automated actions, direct button_validate on internal
#     transfers). The delivery_journal_entry_ids guard prevents duplicates.
# """
# import logging
# from odoo import models
#
# _logger = logging.getLogger(__name__)
#
#
# # ── Analytic helpers ──────────────────────────────────────────────────────────
#
# def _get_analytic_from_picking(picking):
#     """
#     Resolve the analytic account for a picking from its own warehouse.
#     Two strategies tried in order:
#
#     1. picking_type_id → warehouse_id → analytic_account_id
#        (direct, reliable when picking_type is set).
#
#     2. Source location → match against all warehouses' lot_stock_id or
#        view_location child (fallback for edge cases).
#
#     Returns the analytic account record or False.
#     Never uses env.user — that is unreliable in POS background processes.
#     """
#     if not picking:
#         return False
#
#     # Strategy 1: via picking_type → warehouse
#     picking_type = picking.picking_type_id
#     if picking_type:
#         wh = getattr(picking_type, 'warehouse_id', False)
#         if wh and getattr(wh, 'analytic_account_id', False):
#             _logger.debug(
#                 "POS analytic: picking[%s] → picking_type[%s] → wh[%s] → %s",
#                 picking.name, picking_type.name,
#                 wh.name, wh.analytic_account_id.name,
#             )
#             return wh.analytic_account_id
#
#     # Strategy 2: match source location against warehouses
#     src = picking.location_id
#     if src:
#         warehouses = picking.env['stock.warehouse'].search([
#             ('analytic_account_id', '!=', False),
#             ('company_id', '=', picking.company_id.id),
#         ])
#         for wh in warehouses:
#             if src.id == wh.lot_stock_id.id or src._child_of(wh.view_location_id):
#                 _logger.debug(
#                     "POS analytic (location fallback): picking[%s] → loc[%s] "
#                     "→ wh[%s] → %s",
#                     picking.name, src.name,
#                     wh.name, wh.analytic_account_id.name,
#                 )
#                 return wh.analytic_account_id
#
#     _logger.warning(
#         "POS analytic: no analytic found for picking[%s] (picking_type=%s)",
#         picking.name,
#         picking.picking_type_id.name if picking.picking_type_id else 'None',
#     )
#     return False
#
#
# def _apply_analytic_to_move(move, analytic, label=''):
#     """
#     Stamp analytic_distribution on all account.move.line records of a
#     posted account.move.
#
#     Uses sudo() + context flags to bypass the posted-move write restriction.
#     Only adds the analytic if it is not already present (idempotent).
#     """
#     if not move or not analytic:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = {**existing, key: 100.0}
#             try:
#                 line.sudo().with_context(
#                     check_move_validity=False,
#                     skip_account_move_synchronization=True,
#                 ).analytic_distribution = new_dist
#                 _logger.debug(
#                     "Analytic applied: %s → %s line %s (account %s)",
#                     analytic.name, label, line.id, line.account_id.code,
#                 )
#             except Exception:
#                 _logger.warning(
#                     "Could not apply analytic to %s line %s",
#                     label, line.id, exc_info=True,
#                 )
#
#
# # ── POS Order hook ─────────────────────────────────────────────────────────────
#
# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     def _process_saved_order(self, draft):
#         """
#         Hook at the end of POS order processing, after _create_order_picking().
#
#         We create delivery valuation entries here rather than in _action_done
#         because picking.pos_order_id is not yet set when _action_done fires
#         during POS sync_from_ui, making the skip-check unreliable.
#         """
#         res = super()._process_saved_order(draft)
#         if not draft:
#             self._create_anglo_saxon_pos_delivery_entries()
#         return res
#
#     def _create_anglo_saxon_pos_delivery_entries(self):
#         """
#         Create DR 121200 / CR 110100 entries for done outgoing POS pickings
#         that do not yet have a delivery journal entry (guard against duplicates).
#         """
#         for order in self:
#             eligible = order.picking_ids.filtered(
#                 lambda p: (
#                     p.state == 'done'
#                     and p.picking_type_code == 'outgoing'
#                     and not p.sudo().delivery_journal_entry_ids
#                 )
#             )
#
#             if not eligible:
#                 _logger.debug(
#                     "Anglo-Saxon POS: no eligible pickings for order '%s'.",
#                     order.name,
#                 )
#                 continue
#
#             for picking in eligible:
#                 try:
#                     picking._create_delivery_valuation_entry()
#
#                     # Apply analytic from picking's own warehouse immediately.
#                     analytic = _get_analytic_from_picking(picking)
#                     if analytic:
#                         for entry in picking.sudo().delivery_journal_entry_ids:
#                             _apply_analytic_to_move(
#                                 entry, analytic,
#                                 label='pos_delivery_%s' % picking.name,
#                             )
#
#                     _logger.info(
#                         "Anglo-Saxon POS: delivery valuation created for "
#                         "picking '%s' (order '%s') analytic=%s",
#                         picking.name, order.name,
#                         analytic.name if analytic else 'None',
#                     )
#                 except Exception:
#                     _logger.error(
#                         "Anglo-Saxon POS: failed for picking '%s' (order '%s')",
#                         picking.name, order.name, exc_info=True,
#                     )
#
#
# # ── Non-POS fallback via _action_done ──────────────────────────────────────────
#
# class StockPickingPos(models.Model):
#     _inherit = 'stock.picking'
#
#     def _action_done(self):
#         """
#         Fallback for outgoing pickings validated programmatically (schedulers,
#         automated actions, internal transfers button_validate).
#
#         POS pickings are handled by PosOrder._process_saved_order() above.
#         The delivery_journal_entry_ids guard prevents double-posting if a POS
#         picking slips through here as well.
#         """
#         res = super()._action_done()
#
#         for picking in self:
#             if picking.state != 'done':
#                 continue
#             if picking.picking_type_code != 'outgoing':
#                 continue
#
#             picking_sudo = picking.sudo()
#
#             if picking_sudo.delivery_journal_entry_ids:
#                 # Entry already exists (created by _process_saved_order or
#                 # button_validate). Apply analytic in case it was missed.
#                 analytic = _get_analytic_from_picking(picking)
#                 if analytic:
#                     for entry in picking_sudo.delivery_journal_entry_ids:
#                         _apply_analytic_to_move(
#                             entry, analytic,
#                             label='existing_%s' % picking.name,
#                         )
#                 continue
#
#             # No entry yet — create it now (non-POS path)
#             try:
#                 picking._create_delivery_valuation_entry()
#
#                 analytic = _get_analytic_from_picking(picking)
#                 if analytic:
#                     for entry in picking_sudo.delivery_journal_entry_ids:
#                         _apply_analytic_to_move(
#                             entry, analytic,
#                             label='action_done_%s' % picking.name,
#                         )
#
#                 _logger.info(
#                     "Anglo-Saxon _action_done: delivery valuation created for "
#                     "picking '%s' analytic=%s",
#                     picking.name,
#                     analytic.name if analytic else 'None',
#                 )
#             except Exception:
#                 _logger.error(
#                     "Anglo-Saxon _action_done: failed for picking '%s'",
#                     picking.name, exc_info=True,
#                 )
#
#         return res
# -*- coding: utf-8 -*-
"""
pos_stock_picking.py  (v4 — definitive fix)

ROOT CAUSE (confirmed from logs v3):
    _action_done fires for KDTY/POS/00059 BEFORE _process_saved_order.
    At that moment pos_order_id is NOT yet set on the picking.
    Origin check also failed — origin was not yet set or didn't match.
    Result: _action_done created a WRONG sale entry (STJ/0003) for the
    return picking, then _process_saved_order created the CORRECT return
    entry (STJ/0004) — giving 3 total entries instead of 2.

THE FIX (v4):
    Detect POS pickings in _action_done by their NAME pattern:
        POS pickings are always named like 'KDTY/POS/00059', 'WH/OUT/00012'
        where they contain '/POS/' in the name.
    This is reliable even before pos_order_id is set.

    Skip ALL pickings whose name contains '/POS/' in _action_done.
    Let _process_saved_order handle them with full order context.

    _process_saved_order uses receipt_journal_entry_ids as guard for
    returns so even if _action_done slips through, the return entry
    won't be duplicated.

ENTRY DIRECTIONS:
    SALE:   DR 365000 Stock Interim (Delivered)  /  CR 226000 Stock Valuation
    RETURN: DR 226000 Stock Valuation             /  CR 365000 Stock Interim
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_analytic_from_picking(picking):
    if not picking:
        return False
    picking_type = picking.picking_type_id
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            return wh.analytic_account_id
    src = picking.location_id
    if src:
        warehouses = picking.env['stock.warehouse'].search([
            ('analytic_account_id', '!=', False),
            ('company_id', '=', picking.company_id.id),
        ])
        for wh in warehouses:
            if src.id == wh.lot_stock_id.id or src._child_of(wh.view_location_id):
                return wh.analytic_account_id
    _logger.warning("POS analytic: no analytic found for picking[%s]", picking.name)
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        if key not in existing:
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = {**existing, key: 100.0}
            except Exception:
                _logger.warning("Could not apply analytic to %s line %s", label, line.id, exc_info=True)


def _is_pos_picking(picking):
    """
    Detect if a picking belongs to POS by its name pattern.
    POS pickings are always named with '/POS/' in the name:
        e.g. KDTY/POS/00059, WH/POS/00001
    This check is reliable even before pos_order_id is set on the picking.
    """
    return '/POS/' in (picking.name or '')


def _is_pos_refund_order(order):
    """
    Detect if a pos.order is a REFUND/RETURN order.
    Uses 4 detection strategies in order of reliability.
    """
    if not order:
        return False

    # 1. Explicit is_return_order flag (Odoo 17+)
    if getattr(order, 'is_return_order', False):
        _logger.info("POS refund detected (is_return_order): order '%s'", order.name)
        return True

    # 2. refunded_order_ids — this order refunds another order
    if getattr(order, 'refunded_order_ids', False) and order.refunded_order_ids:
        _logger.info("POS refund detected (refunded_order_ids): order '%s'", order.name)
        return True

    # 3. Name or pos_reference contains 'REFUND'
    order_name = (order.name or '').upper()
    pos_ref = (getattr(order, 'pos_reference', '') or '').upper()
    if 'REFUND' in order_name or 'REFUND' in pos_ref:
        _logger.info("POS refund detected (name/ref): order '%s'", order.name)
        return True

    # 4. All lines have qty <= 0 and at least one < 0
    lines = getattr(order, 'lines', [])
    if lines and all(l.qty <= 0 for l in lines) and any(l.qty < 0 for l in lines):
        _logger.info("POS refund detected (negative qtys): order '%s'", order.name)
        return True

    return False


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """
        Hook AFTER _create_order_picking(). At this point:
        - The picking exists and is done
        - We have full POS order context to detect refunds
        """
        res = super()._process_saved_order(draft)
        if not draft:
            self._create_anglo_saxon_pos_valuation_entries()
        return res

    def _create_anglo_saxon_pos_valuation_entries(self):
        """
        Route each done POS picking to correct valuation method.
        Uses guards to prevent double-posting if _action_done already ran.

        SALE guard:   delivery_journal_entry_ids  (must be empty to proceed)
        RETURN guard: receipt_journal_entry_ids   (must be empty to proceed)
        """
        for order in self:
            is_refund = _is_pos_refund_order(order)

            eligible = order.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
            )
            if not eligible:
                continue

            for picking in eligible:
                picking_sudo = picking.sudo()

                if is_refund:
                    # RETURN: DR Stock Valuation / CR Stock Interim
                    if picking_sudo.receipt_journal_entry_ids:
                        _logger.debug(
                            "Anglo-Saxon POS return: already posted for '%s' — skip.",
                            picking.name,
                        )
                        continue
                    # Also reverse any wrong sale entry created by _action_done
                    if picking_sudo.delivery_journal_entry_ids:
                        _logger.warning(
                            "Anglo-Saxon POS return: picking '%s' has a WRONG sale "
                            "entry from _action_done — reversing it now.",
                            picking.name,
                        )
                        for wrong_entry in picking_sudo.delivery_journal_entry_ids:
                            try:
                                wrong_entry.sudo().button_cancel()
                                wrong_entry.sudo().button_draft()
                                wrong_entry.sudo().unlink()
                                _logger.info(
                                    "Anglo-Saxon POS: deleted wrong sale entry for "
                                    "return picking '%s'.", picking.name,
                                )
                            except Exception:
                                _logger.error(
                                    "Anglo-Saxon POS: could not delete wrong entry "
                                    "for picking '%s'.", picking.name, exc_info=True,
                                )
                        picking_sudo.delivery_journal_entry_ids = [(5,)]
                    try:
                        picking._create_return_valuation_entry()
                        analytic = _get_analytic_from_picking(picking)
                        if analytic:
                            for entry in picking_sudo.receipt_journal_entry_ids:
                                _apply_analytic_to_move(entry, analytic, label='pos_return_%s' % picking.name)
                        _logger.info(
                            "Anglo-Saxon POS: RETURN valuation created for "
                            "picking '%s' (order '%s')", picking.name, order.name,
                        )
                    except Exception:
                        _logger.error(
                            "Anglo-Saxon POS: RETURN failed for picking '%s' (order '%s')",
                            picking.name, order.name, exc_info=True,
                        )

                else:
                    # SALE: DR Stock Interim / CR Stock Valuation
                    if picking_sudo.delivery_journal_entry_ids:
                        _logger.debug(
                            "Anglo-Saxon POS sale: already posted for '%s' — skip.",
                            picking.name,
                        )
                        continue
                    try:
                        picking._create_delivery_valuation_entry()
                        analytic = _get_analytic_from_picking(picking)
                        if analytic:
                            for entry in picking_sudo.delivery_journal_entry_ids:
                                _apply_analytic_to_move(entry, analytic, label='pos_delivery_%s' % picking.name)
                        _logger.info(
                            "Anglo-Saxon POS: SALE valuation created for "
                            "picking '%s' (order '%s')", picking.name, order.name,
                        )
                    except Exception:
                        _logger.error(
                            "Anglo-Saxon POS: SALE failed for picking '%s' (order '%s')",
                            picking.name, order.name, exc_info=True,
                        )


class StockPickingPos(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """
        Fallback for NON-POS outgoing pickings only.

        CRITICAL (v4): Skip ALL POS pickings detected by name pattern '/POS/'.
        This is the ONLY reliable check at _action_done time because:
          - pos_order_id is NOT yet set (set later by _create_order_picking)
          - origin may not yet be set or may not match
          - BUT the picking name is always set and always contains '/POS/'
            for POS pickings (e.g. KDTY/POS/00059)

        POS pickings are fully handled by _process_saved_order which runs
        after _action_done with full order context.
        """
        res = super()._action_done()

        for picking in self:
            if picking.state != 'done':
                continue
            if picking.picking_type_code != 'outgoing':
                continue

            # CRITICAL: Skip POS pickings by name pattern
            if _is_pos_picking(picking):
                _logger.debug(
                    "Anglo-Saxon _action_done: SKIP POS picking '%s' "
                    "(name contains /POS/) → handled by _process_saved_order.",
                    picking.name,
                )
                continue

            picking_sudo = picking.sudo()

            # Non-POS outgoing delivery
            if picking_sudo.delivery_journal_entry_ids:
                analytic = _get_analytic_from_picking(picking)
                if analytic:
                    for entry in picking_sudo.delivery_journal_entry_ids:
                        _apply_analytic_to_move(entry, analytic, label='existing_%s' % picking.name)
                continue

            try:
                picking._create_delivery_valuation_entry()
                analytic = _get_analytic_from_picking(picking)
                if analytic:
                    for entry in picking_sudo.delivery_journal_entry_ids:
                        _apply_analytic_to_move(entry, analytic, label='action_done_%s' % picking.name)
                _logger.info(
                    "Anglo-Saxon _action_done: SALE valuation created for "
                    "non-POS picking '%s'", picking.name,
                )
            except Exception:
                _logger.error(
                    "Anglo-Saxon _action_done: failed for '%s'",
                    picking.name, exc_info=True,
                )

        return res