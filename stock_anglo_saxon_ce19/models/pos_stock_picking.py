# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Hooks into POS order processing to create Anglo-Saxon
delivery valuation entries (DR 121200 / CR 110100).

Odoo 19 POS flow:
  sync_from_ui
    -> _process_order
       -> _process_saved_order
          -> action_pos_order_paid   (invoice/payment)
          -> _create_order_picking   (picking created HERE)

So we must hook AFTER _create_order_picking, i.e. at end of _process_saved_order.

FIX:
  _action_done was processing POS pickings because picking.pos_order_id is not
  yet set when _action_done fires during POS sync_from_ui. The skip check
  therefore never triggered, and env.user (Administrator = wrong warehouse)
  was used to resolve the analytic.

  Solution: Apply the analytic immediately after creating the delivery entry,
  reading the warehouse from picking.picking_type_id.warehouse_id directly.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_analytic_from_picking(picking):
    """
    Resolve analytic account from the picking's own warehouse.
    Uses picking_type_id → warehouse_id → analytic_account_id.
    Never uses env.user (unreliable for background/POS processes).
    """
    if not picking:
        return False

    # Strategy 1: picking_type_id → warehouse_id
    picking_type = picking.picking_type_id
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug(
                'POS stock analytic: picking[%s] → picking_type[%s]'
                ' → wh[%s] → %s',
                picking.name, picking_type.name,
                wh.name, wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # Strategy 2: match by source location
    src_location = picking.location_id
    if src_location:
        warehouses = picking.env['stock.warehouse'].search([
            ('analytic_account_id', '!=', False),
            ('company_id', '=', picking.company_id.id),
        ])
        for wh in warehouses:
            if src_location.id == wh.lot_stock_id.id or \
               src_location._child_of(wh.view_location_id):
                _logger.debug(
                    'POS stock analytic (fallback): picking[%s]'
                    ' → location[%s] → wh[%s] → %s',
                    picking.name, src_location.name,
                    wh.name, wh.analytic_account_id.name,
                )
                return wh.analytic_account_id

    _logger.warning(
        'POS stock analytic: no analytic found for picking[%s]'
        ' (picking_type=%s)',
        picking.name,
        picking.picking_type_id.name if picking.picking_type_id else 'None',
    )
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on all account lines of an account.move.
    Uses sudo() + context flags to bypass posted-move restrictions.
    """
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
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
                    'POS stock analytic %s → %s line %s (%s)',
                    analytic.name, label, line.id,
                    line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to %s line %s: %s',
                    label, line.id, e,
                )


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """
        Hook after _create_order_picking() to create delivery valuation.
        In Odoo 19, picking is created inside this method AFTER
        action_pos_order_paid(), so we run our logic at the very end.
        """
        res = super()._process_saved_order(draft)
        _logger.info(
            "Anglo-Saxon POS: _process_saved_order called for '%s' draft=%s",
            self.name, draft
        )
        if not draft:
            self._create_anglo_saxon_pos_delivery_entries()
        return res

    def _create_anglo_saxon_pos_delivery_entries(self):
        """Create DR 121200 / CR 110100 for POS outgoing pickings."""
        for order in self:
            _logger.info(
                "Anglo-Saxon POS: checking order '%s' picking_ids=%s",
                order.name,
                order.picking_ids.mapped('name')
            )
            pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done'
                and p.picking_type_code == 'outgoing'
                and not p.delivery_journal_entry_ids
            )
            _logger.info(
                "Anglo-Saxon POS: order '%s' found %d eligible pickings",
                order.name, len(pickings)
            )
            for picking in pickings:
                try:
                    picking._create_delivery_valuation_entry()
                    # Apply analytic immediately from picking's own warehouse
                    # NOT env.user — POS runs as background/admin user
                    analytic = _get_analytic_from_picking(picking)
                    if analytic:
                        for entry in picking.delivery_journal_entry_ids:
                            _apply_analytic_to_move(
                                entry, analytic,
                                label='pos_delivery_%s' % picking.name,
                            )
                    _logger.info(
                        "Anglo-Saxon POS: Created delivery valuation "
                        "for picking '%s' (order '%s') analytic=%s",
                        picking.name, order.name,
                        analytic.name if analytic else 'None',
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon POS: Failed for picking '%s': %s",
                        picking.name, str(e), exc_info=True
                    )


class StockPickingPos(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """
        Fallback hook for non-POS outgoing pickings validated
        programmatically (scheduler, internal transfers).

        NOTE: picking.pos_order_id is NOT reliably set when _action_done fires
        during POS sync_from_ui, so the skip check may not work. However since
        we apply analytic from picking's own warehouse (not env.user), even if
        a POS picking slips through here the analytic will still be correct.
        The delivery_journal_entry_ids guard prevents duplicate entries.
        """
        res = super()._action_done()
        for picking in self:
            if picking.state != 'done':
                continue
            if picking.picking_type_code != 'outgoing':
                continue
            if picking.delivery_journal_entry_ids:
                # Already created (by _process_saved_order or button_validate)
                # Still apply analytic in case it was missed
                analytic = _get_analytic_from_picking(picking)
                if analytic:
                    for entry in picking.delivery_journal_entry_ids:
                        _apply_analytic_to_move(
                            entry, analytic,
                            label='delivery_existing_%s' % picking.name,
                        )
                continue

            # No entry yet — create it now (non-POS outgoing picking)
            try:
                picking._create_delivery_valuation_entry()
                analytic = _get_analytic_from_picking(picking)
                if analytic:
                    for entry in picking.delivery_journal_entry_ids:
                        _apply_analytic_to_move(
                            entry, analytic,
                            label='delivery_action_done_%s' % picking.name,
                        )
                _logger.info(
                    "Anglo-Saxon _action_done: Created delivery valuation"
                    " for '%s' analytic=%s",
                    picking.name,
                    analytic.name if analytic else 'None',
                )
            except Exception as e:
                _logger.error(
                    "Anglo-Saxon _action_done: Failed '%s': %s",
                    picking.name, str(e), exc_info=True
                )
        return res