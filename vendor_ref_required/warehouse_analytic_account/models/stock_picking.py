# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_analytic_from_picking(picking):
    """
    Resolve the correct analytic account from the picking itself,
    NOT from env.user.

    Priority:
    1. picking.picking_type_id → warehouse_id → analytic_account_id
    2. Source location fallback — search warehouses by location match

    Why NOT env.user:
    POS pickings are validated by a background process during session sync.
    env.user at that point is Administrator whose default warehouse may differ
    from the actual POS warehouse, causing wrong analytic to be applied.
    """
    if not picking:
        return False

    # Strategy 1: picking_type_id → warehouse_id (most direct and reliable)
    picking_type = picking.picking_type_id
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug(
                'Stock analytic STRATEGY 1: picking[%s] → picking_type[%s]'
                ' → wh[%s] → %s',
                picking.name, picking_type.name,
                wh.name, wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # Strategy 2: match by source location against known warehouses
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
                    'Stock analytic STRATEGY 2: picking[%s] → location[%s]'
                    ' → wh[%s] → %s',
                    picking.name, src_location.name,
                    wh.name, wh.analytic_account_id.name,
                )
                return wh.analytic_account_id

    _logger.warning(
        'Stock analytic: no warehouse analytic found for picking[%s]'
        ' (picking_type=%s, location=%s)',
        picking.name,
        picking.picking_type_id.name if picking.picking_type_id else 'None',
        picking.location_id.name if picking.location_id else 'None',
    )
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on ALL account lines of an account.move.
    Uses sudo() + context flags to bypass posted-move restrictions.
    Skips lines that already carry this analytic.
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
                    'Stock analytic %s → %s line %s (%s)',
                    analytic.name, label, line.id,
                    line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to %s line %s: %s',
                    label, line.id, e,
                )


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        After picking validation, apply the correct warehouse analytic
        to all generated journal entries (receipt and delivery).
        Reads warehouse from picking's own picking_type_id, NOT env.user.
        """
        result = super().button_validate()
        for picking in self:
            if picking.state != 'done':
                continue
            analytic = _get_analytic_from_picking(picking)
            if not analytic:
                continue
            for entry in picking.receipt_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='receipt_%s' % picking.name,
                )
            for entry in picking.delivery_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='delivery_%s' % picking.name,
                )
        return result

    def _action_done(self):
        """
        Secondary hook for pickings validated programmatically
        (scheduler, internal transfers). Same warehouse-from-picking logic.
        """
        result = super()._action_done()
        for picking in self:
            if picking.state != 'done':
                continue
            analytic = _get_analytic_from_picking(picking)
            if not analytic:
                continue
            for entry in picking.receipt_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='receipt_action_done_%s' % picking.name,
                )
            for entry in picking.delivery_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='delivery_action_done_%s' % picking.name,
                )
        return result