# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_warehouse_from_location(env, location, company_id):
    """
    Resolve the warehouse that owns a given stock location by checking:
    1. Direct match against warehouse.lot_stock_id
    2. Child-of warehouse.view_location_id (walks parent chain as fallback)
    """
    warehouses = env['stock.warehouse'].search([
        ('analytic_account_id', '!=', False),
        ('company_id', '=', company_id),
    ])
    for wh in warehouses:
        if location.id == wh.lot_stock_id.id:
            return wh
        try:
            if location._child_of(wh.view_location_id):
                return wh
        except Exception:
            loc = location
            while loc:
                if loc.id == wh.view_location_id.id:
                    return wh
                loc = loc.location_id or False
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on all account.move.line records.
    Uses sudo() + context flags to bypass posted-move write restriction.
    Skips lines already carrying this analytic.
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
                    'Inventory analytic %s -> %s line %s (%s)',
                    analytic.name, label, line.id,
                    line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply inventory analytic to %s line %s: %s',
                    label, line.id, e,
                )


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _apply_inventory(self, date=None):
        """
        Override _apply_inventory to stamp the warehouse analytic account
        on all STJ (inventory adjustment) journal entries generated.

        In Odoo 19, action_apply_inventory() passes a `date` argument, so
        we accept and forward it via *args to stay version-safe.

        We snapshot existing account.move IDs before super(), then diff
        afterward to find newly created STJ entries to tag.
        """
        # Snapshot existing general journal entry IDs
        existing_move_ids = set(
            self.env['account.move'].search([
                ('journal_id.type', '=', 'general'),
            ]).ids
        )

        # Call super with or without date depending on what was passed
        if date is not None:
            result = super()._apply_inventory(date)
        else:
            result = super()._apply_inventory()

        # Find newly created STJ account.move records
        new_moves = self.env['account.move'].search([
            ('id', 'not in', list(existing_move_ids)),
            ('journal_id.type', '=', 'general'),
        ])

        if not new_moves:
            return result

        for move in new_moves:
            analytic = self._get_inventory_analytic(move)
            if analytic:
                _apply_analytic_to_move(
                    move, analytic,
                    label='inventory_adj_%s' % (move.name or move.id),
                )
            else:
                _logger.warning(
                    'Inventory analytic: no warehouse analytic found for STJ move %s',
                    move.name,
                )

        return result

    def _get_inventory_analytic(self, account_move):
        """
        Resolve the analytic account for an inventory-adjustment account.move.

        In Odoo 19, the stock.move -> account.move link is stored on
        account.move.line as 'stock_move_id' (Many2one on the line level).
        There is NO 'account_move_ids' or 'account_move_id' field on stock.move.

        Strategy:
        1. Read account.move.line.stock_move_id from the move's own lines
           to get the originating stock.move records — no search on stock.move.
        2. From each stock.move, resolve location -> warehouse -> analytic.
        3. Fallback: use the quants' own location_id directly.
        """
        env = self.env
        company_id = account_move.company_id.id

        # Strategy 1: read stock_move_id from account.move.line (Odoo 19)
        stock_move_ids = set()
        for line in account_move.line_ids:
            sm = getattr(line, 'stock_move_id', False)
            if sm:
                stock_move_ids.add(sm.id)

        if stock_move_ids:
            stock_moves = env['stock.move'].browse(list(stock_move_ids))
            for sm in stock_moves:
                # For inventory adjustments, destination is the stock location
                for loc in (sm.location_dest_id, sm.location_id):
                    if not loc:
                        continue
                    wh = _get_warehouse_from_location(env, loc, company_id)
                    if wh:
                        _logger.debug(
                            'Inventory analytic: move %s -> stock.move %s'
                            ' -> loc %s -> wh %s -> %s',
                            account_move.name, sm.id, loc.name,
                            wh.name, wh.analytic_account_id.name,
                        )
                        return wh.analytic_account_id

        # Fallback: use the quants' own location_id directly
        for quant in self:
            loc = quant.location_id
            if not loc:
                continue
            wh = _get_warehouse_from_location(env, loc, company_id)
            if wh:
                _logger.debug(
                    'Inventory analytic (quant fallback): quant %s -> loc %s'
                    ' -> wh %s -> %s',
                    quant.id, loc.name, wh.name, wh.analytic_account_id.name,
                )
                return wh.analytic_account_id

        return False