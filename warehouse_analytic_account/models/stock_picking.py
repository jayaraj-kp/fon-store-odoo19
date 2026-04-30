# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import fields, models

_logger = logging.getLogger(__name__)


def _apply_analytic_to_journal_lines(env, analytic, label_hint=''):
    if not analytic:
        return
    key = str(analytic.id)
    since = (datetime.now() - timedelta(seconds=15)).strftime('%Y-%m-%d %H:%M:%S')
    acc_moves = env['account.move'].search([
        ('move_type', '=', 'entry'),
        ('state', '=', 'posted'),
        ('create_date', '>=', since),
    ])
    for acc_move in acc_moves:
        for line in acc_move.line_ids.filtered(lambda l: l.account_id):
            existing = line.analytic_distribution or {}
            if key not in existing:
                new_dist = dict(existing)
                new_dist[key] = 100.0
                try:
                    line.analytic_distribution = new_dist
                except Exception as e:
                    _logger.warning('Could not set analytic on line %s: %s', line.id, e)


def _apply_analytic_to_move_direct(env, analytic, move, label_hint=''):
    if not analytic or not move:
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
                    'Analytic %s applied to %s line %s [%s]',
                    analytic.name, move.name, line.id, label_hint,
                )
            except Exception as e:
                _logger.warning('Could not set analytic on line %s: %s', line.id, e)


# ── Top-level helper (NOT inside any class) ──────────────────────────────────
def _apply_analytic_to_move_lines(move, analytic):
    """Apply analytic distribution to all lines of an account.move."""
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
                    'STJ analytic %s applied to %s line %s',
                    analytic.name, move.name, line.id,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to STJ line %s: %s', line.id, e
                )


class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        index=True,
    )


_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def _get_scrap_analytic(self):
        wh = _get_user_warehouse(self.env.user)
        if wh and getattr(wh, 'analytic_account_id', False):
            return wh.analytic_account_id
        for scrap in self:
            wh = getattr(getattr(scrap, 'picking_type_id', False), 'warehouse_id', False)
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id
            wh = getattr(scrap.location_id, 'warehouse_id', False)
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id
        return False

    def action_validate(self):
        scrap_analytics = {scrap.id: scrap._get_scrap_analytic() for scrap in self}
        result = super().action_validate()
        for scrap in self:
            analytic = scrap_analytics.get(scrap.id)
            if not analytic:
                continue
            scrap_move = getattr(scrap, 'move_id', False)
            if scrap_move and scrap_move.account_move_ids:
                for acc_move in scrap_move.account_move_ids:
                    _apply_analytic_to_move_direct(self.env, analytic, acc_move, 'scrap')
            else:
                _apply_analytic_to_journal_lines(self.env, analytic, 'scrap')
        return result


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_quant_analytic(self):
        for quant in self:
            wh = quant.location_id.warehouse_id
            if wh and wh.analytic_account_id:
                return wh.analytic_account_id
        return False

    def action_apply_inventory(self):
        analytic = self._get_quant_analytic()
        result = super().action_apply_inventory()
        _apply_analytic_to_journal_lines(self.env, analytic, 'action_apply_inventory')
        return result

    def _apply_inventory(self, date=None):
        analytic = self._get_quant_analytic()
        result = super()._apply_inventory(date) if date is not None else super()._apply_inventory()
        _apply_analytic_to_journal_lines(self.env, analytic, '_apply_inventory')
        return result


# ── Single StockPicking class — handles both button_validate AND STJ entries ──
class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _get_warehouse_analytic_account(self):
        wh = (
            self.location_id.warehouse_id
            or self.picking_type_id.warehouse_id
        )
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def button_validate(self):
        result = super().button_validate()
        for picking in self:
            analytic = picking._get_warehouse_analytic_account()
            if not analytic:
                continue
            picking.move_ids.filtered(
                lambda m: not m.analytic_account_id
            ).write({'analytic_account_id': analytic.id})
            _apply_analytic_to_journal_lines(
                self.env, analytic, 'picking_%s' % picking.name
            )
        return result

    def _create_delivery_valuation_entry(self):
        """Apply warehouse analytic to Anglo-Saxon delivery STJ entries."""
        res = super()._create_delivery_valuation_entry()
        for picking in self:
            analytic = picking._get_warehouse_analytic_account()
            if not analytic:
                continue
            for entry in picking.delivery_journal_entry_ids:
                _apply_analytic_to_move_lines(entry, analytic)
                _logger.info(
                    'STJ delivery analytic %s applied to %s',
                    analytic.name, entry.name
                )
        return res

    def _create_receipt_valuation_entry(self):
        """Apply warehouse analytic to Anglo-Saxon receipt STJ entries."""
        res = super()._create_receipt_valuation_entry()
        for picking in self:
            analytic = picking._get_warehouse_analytic_account()
            if not analytic:
                continue
            for entry in picking.receipt_journal_entry_ids:
                _apply_analytic_to_move_lines(entry, analytic)
                _logger.info(
                    'STJ receipt analytic %s applied to %s',
                    analytic.name, entry.name
                )
        return res
