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
pos_stock_picking.py

Hooks into POS order processing to create Anglo-Saxon delivery valuation
entries immediately after a POS picking is completed.

SALE (outgoing):
    DR  365000  Stock Interim (Delivered)
    CR  226000  Stock Valuation

RETURN / REFUND (incoming from customer — reverse of above):
    DR  226000  Stock Valuation      ← stock value comes BACK
    CR  365000  Stock Interim        ← clears the interim

FIX (v2):
    Original module treated ALL pickings as outgoing sales — returns were
    posted in the same direction as sales, leaving Stock Interim with a
    permanent debit balance and Stock Valuation continuously reduced.

    This version detects POS return pickings by:
      1. picking_type_code == 'incoming'  AND
      2. picking has a pos_order_id whose return_order_ids / origin suggests
         a refund, OR the POS order itself is linked to a refund order.
    And posts the REVERSED entry for those pickings.

ODOO 19 POS FLOW:
    sync_from_ui
      └─ _process_order
           └─ _process_saved_order
                ├─ action_pos_order_paid   (payment/invoice)
                └─ _create_order_picking   (picking created + done)

WHY _process_saved_order and not _action_done:
    picking.pos_order_id is NOT reliably set when _action_done fires during
    sync_from_ui. We hook _process_saved_order instead.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


# ── Analytic helpers ──────────────────────────────────────────────────────────

def _get_analytic_from_picking(picking):
    """
    Resolve the analytic account for a picking from its own warehouse.
    Never uses env.user — unreliable in POS background processes.
    """
    if not picking:
        return False

    # Strategy 1: via picking_type → warehouse
    picking_type = picking.picking_type_id
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug(
                "POS analytic: picking[%s] → picking_type[%s] → wh[%s] → %s",
                picking.name, picking_type.name,
                wh.name, wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # Strategy 2: match source location against warehouses
    src = picking.location_id
    if src:
        warehouses = picking.env['stock.warehouse'].search([
            ('analytic_account_id', '!=', False),
            ('company_id', '=', picking.company_id.id),
        ])
        for wh in warehouses:
            if src.id == wh.lot_stock_id.id or src._child_of(wh.view_location_id):
                _logger.debug(
                    "POS analytic (location fallback): picking[%s] → loc[%s] "
                    "→ wh[%s] → %s",
                    picking.name, src.name,
                    wh.name, wh.analytic_account_id.name,
                )
                return wh.analytic_account_id

    _logger.warning(
        "POS analytic: no analytic found for picking[%s] (picking_type=%s)",
        picking.name,
        picking.picking_type_id.name if picking.picking_type_id else 'None',
    )
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on all account.move.line records of a
    posted account.move. Idempotent.
    """
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        if key not in existing:
            new_dist = {**existing, key: 100.0}
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
            except Exception:
                _logger.warning(
                    "Could not apply analytic to %s line %s",
                    label, line.id, exc_info=True,
                )


# ── Return detection ──────────────────────────────────────────────────────────

def _is_pos_return_picking(picking):
    """
    Determine if a picking belongs to a POS RETURN/REFUND order.

    A POS return picking is an INCOMING picking (stock comes back from
    customer to warehouse). Detection strategy:

    1. picking_type_code == 'incoming'  — stock moving back from customer
    2. At least one of:
       a. The linked POS order has return_order_ids (Odoo 17+ field)
       b. The picking's origin contains 'Return' or 'Refund'
       c. The POS order's pos_reference contains 'REFUND'
       d. The picking's location_dest_id is a stock/internal location
          AND location_id is a customer location (classic return flow)

    Returns True if this is a return picking, False otherwise.
    """
    if not picking:
        return False

    # Outgoing = normal sale, not a return
    if picking.picking_type_code == 'outgoing':
        return False

    # Only consider incoming pickings for return detection
    if picking.picking_type_code != 'incoming':
        return False

    # Check location: customer → stock = return
    src_usage = picking.location_id.usage if picking.location_id else ''
    dest_usage = picking.location_dest_id.usage if picking.location_dest_id else ''
    if src_usage == 'customer' and dest_usage == 'internal':
        _logger.info(
            "POS return detected (location): picking[%s] %s→%s",
            picking.name, src_usage, dest_usage,
        )
        return True

    # Check origin string
    origin = (picking.origin or '').lower()
    if 'return' in origin or 'refund' in origin:
        _logger.info(
            "POS return detected (origin): picking[%s] origin='%s'",
            picking.name, picking.origin,
        )
        return True

    # Check linked POS order
    pos_order = getattr(picking, 'pos_order_id', False)
    if pos_order:
        # Odoo 17+: return_order_ids field
        if getattr(pos_order, 'return_order_ids', False):
            _logger.info(
                "POS return detected (return_order_ids): picking[%s]",
                picking.name,
            )
            return True
        # POS reference contains REFUND
        pos_ref = (getattr(pos_order, 'pos_reference', '') or '').upper()
        if 'REFUND' in pos_ref:
            _logger.info(
                "POS return detected (pos_reference): picking[%s] ref='%s'",
                picking.name, pos_ref,
            )
            return True
        # Order name contains REFUND
        order_name = (pos_order.name or '').upper()
        if 'REFUND' in order_name:
            _logger.info(
                "POS return detected (order name): picking[%s] order='%s'",
                picking.name, order_name,
            )
            return True

    return False


# ── POS Order hook ─────────────────────────────────────────────────────────────

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """
        Hook at the end of POS order processing, after _create_order_picking().
        Creates Anglo-Saxon valuation entries for both sales and returns.
        """
        res = super()._process_saved_order(draft)
        if not draft:
            self._create_anglo_saxon_pos_entries()
        return res

    def _create_anglo_saxon_pos_entries(self):
        """
        Create valuation entries for all done POS pickings:
          - Outgoing (sale):   DR Stock Interim / CR Stock Valuation
          - Incoming (return): DR Stock Valuation / CR Stock Interim  ← FIXED
        """
        for order in self:
            for picking in order.picking_ids.filtered(lambda p: p.state == 'done'):
                picking_sudo = picking.sudo()

                is_return = _is_pos_return_picking(picking)

                if is_return:
                    # ── RETURN: use receipt_journal_entry_ids as guard ──
                    if picking_sudo.receipt_journal_entry_ids:
                        _logger.debug(
                            "Anglo-Saxon POS return: entry already exists for "
                            "picking '%s' — skipping.", picking.name,
                        )
                        continue
                    try:
                        picking._create_return_valuation_entry()
                        analytic = _get_analytic_from_picking(picking)
                        if analytic:
                            for entry in picking_sudo.receipt_journal_entry_ids:
                                _apply_analytic_to_move(
                                    entry, analytic,
                                    label='pos_return_%s' % picking.name,
                                )
                        _logger.info(
                            "Anglo-Saxon POS: RETURN valuation created for "
                            "picking '%s' (order '%s')",
                            picking.name, order.name,
                        )
                    except Exception:
                        _logger.error(
                            "Anglo-Saxon POS: RETURN failed for picking '%s' "
                            "(order '%s')",
                            picking.name, order.name, exc_info=True,
                        )

                elif picking.picking_type_code == 'outgoing':
                    # ── SALE: normal outgoing delivery entry ──
                    if picking_sudo.delivery_journal_entry_ids:
                        _logger.debug(
                            "Anglo-Saxon POS sale: entry already exists for "
                            "picking '%s' — skipping.", picking.name,
                        )
                        continue
                    try:
                        picking._create_delivery_valuation_entry()
                        analytic = _get_analytic_from_picking(picking)
                        if analytic:
                            for entry in picking_sudo.delivery_journal_entry_ids:
                                _apply_analytic_to_move(
                                    entry, analytic,
                                    label='pos_delivery_%s' % picking.name,
                                )
                        _logger.info(
                            "Anglo-Saxon POS: SALE valuation created for "
                            "picking '%s' (order '%s')",
                            picking.name, order.name,
                        )
                    except Exception:
                        _logger.error(
                            "Anglo-Saxon POS: SALE failed for picking '%s' "
                            "(order '%s')",
                            picking.name, order.name, exc_info=True,
                        )


# ── Non-POS fallback via _action_done ──────────────────────────────────────────

class StockPickingPos(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """
        Fallback for pickings validated programmatically (schedulers,
        automated actions, button_validate on non-POS transfers).

        POS pickings are handled by PosOrder._process_saved_order() above.
        Guards prevent double-posting.
        """
        res = super()._action_done()

        for picking in self:
            if picking.state != 'done':
                continue

            picking_sudo = picking.sudo()
            is_return = _is_pos_return_picking(picking)

            if is_return:
                # Return picking
                if picking_sudo.receipt_journal_entry_ids:
                    # Already posted — just ensure analytic is stamped
                    analytic = _get_analytic_from_picking(picking)
                    if analytic:
                        for entry in picking_sudo.receipt_journal_entry_ids:
                            _apply_analytic_to_move(
                                entry, analytic,
                                label='existing_return_%s' % picking.name,
                            )
                    continue
                try:
                    picking._create_return_valuation_entry()
                    analytic = _get_analytic_from_picking(picking)
                    if analytic:
                        for entry in picking_sudo.receipt_journal_entry_ids:
                            _apply_analytic_to_move(
                                entry, analytic,
                                label='action_done_return_%s' % picking.name,
                            )
                    _logger.info(
                        "Anglo-Saxon _action_done: RETURN valuation created "
                        "for picking '%s'", picking.name,
                    )
                except Exception:
                    _logger.error(
                        "Anglo-Saxon _action_done: RETURN failed for '%s'",
                        picking.name, exc_info=True,
                    )

            elif picking.picking_type_code == 'outgoing':
                # Normal sale delivery
                if picking_sudo.delivery_journal_entry_ids:
                    analytic = _get_analytic_from_picking(picking)
                    if analytic:
                        for entry in picking_sudo.delivery_journal_entry_ids:
                            _apply_analytic_to_move(
                                entry, analytic,
                                label='existing_%s' % picking.name,
                            )
                    continue
                try:
                    picking._create_delivery_valuation_entry()
                    analytic = _get_analytic_from_picking(picking)
                    if analytic:
                        for entry in picking_sudo.delivery_journal_entry_ids:
                            _apply_analytic_to_move(
                                entry, analytic,
                                label='action_done_%s' % picking.name,
                            )
                    _logger.info(
                        "Anglo-Saxon _action_done: SALE valuation created "
                        "for picking '%s'", picking.name,
                    )
                except Exception:
                    _logger.error(
                        "Anglo-Saxon _action_done: SALE failed for '%s'",
                        picking.name, exc_info=True,
                    )

        return res