# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    """Return the user's default warehouse, trying known field names."""
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


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

        Priority for analytic resolution:
        1. Logged-in user's default warehouse analytic  ← CORRECT for manual
           inventory adjustments done by a branch user.
        2. Location-based warehouse fallback (only if user has no warehouse set).

        In Odoo 19, action_apply_inventory() passes a `date` argument, so
        we accept and forward it.
        """
        # Snapshot existing general journal entry IDs before super()
        existing_move_ids = set(
            self.env['account.move'].search([
                ('journal_id.type', '=', 'general'),
            ]).ids
        )

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

        # --- Resolve analytic ONCE from the user's default warehouse ---
        # This is correct: the person doing the physical count belongs to a
        # branch (warehouse), and the STJ entry should reflect THEIR branch,
        # not the physical location of the product (which may differ).
        user_analytic = False
        wh = _get_user_warehouse(self.env.user)
        if wh and getattr(wh, 'analytic_account_id', False):
            user_analytic = wh.analytic_account_id
            _logger.debug(
                'Inventory analytic: using user[%s] warehouse[%s] -> %s',
                self.env.user.login, wh.name, user_analytic.name,
            )

        for move in new_moves:
            analytic = user_analytic

            # Fallback: resolve from the stock location if user has no warehouse
            if not analytic:
                analytic = self._get_inventory_analytic_from_location(move)

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

    def _get_inventory_analytic_from_location(self, account_move):
        """
        Location-based fallback: resolve analytic by tracing the stock.move
        location back to a warehouse.

        In Odoo 19, account.move.line carries 'stock_move_id' (Many2one).
        We read it via getattr() to stay safe across versions.
        """
        env = self.env
        company_id = account_move.company_id.id

        # Read stock_move_id from account.move.line (Odoo 19 style)
        stock_move_ids = set()
        for line in account_move.line_ids:
            sm = getattr(line, 'stock_move_id', False)
            if sm:
                stock_move_ids.add(sm.id)

        if stock_move_ids:
            stock_moves = env['stock.move'].browse(list(stock_move_ids))
            for sm in stock_moves:
                for loc in (sm.location_dest_id, sm.location_id):
                    if not loc:
                        continue
                    wh = _get_warehouse_from_location(env, loc, company_id)
                    if wh:
                        _logger.debug(
                            'Inventory analytic (loc fallback): move %s'
                            ' -> stock.move %s -> loc %s -> wh %s -> %s',
                            account_move.name, sm.id, loc.name,
                            wh.name, wh.analytic_account_id.name,
                        )
                        return wh.analytic_account_id

        # Last resort: quant's own location
        for quant in self:
            loc = quant.location_id
            if not loc:
                continue
            wh = _get_warehouse_from_location(env, loc, company_id)
            if wh:
                _logger.debug(
                    'Inventory analytic (quant fallback): quant %s'
                    ' -> loc %s -> wh %s -> %s',
                    quant.id, loc.name, wh.name, wh.analytic_account_id.name,
                )
                return wh.analytic_account_id

        return False