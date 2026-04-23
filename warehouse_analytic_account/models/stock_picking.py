# # -*- coding: utf-8 -*-
# import logging
# from odoo import fields, models
#
# _logger = logging.getLogger(__name__)
#
#
# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     analytic_account_id = fields.Many2one(
#         comodel_name='account.analytic.account',
#         string='Analytic Account',
#         help='Analytic account inherited from the source warehouse.',
#         index=True,
#     )
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     def _get_warehouse_analytic_account(self):
#         wh = (
#             self.location_id.warehouse_id
#             or self.picking_type_id.warehouse_id
#         )
#         if wh and wh.analytic_account_id:
#             return wh.analytic_account_id
#         return False
#
#     def button_validate(self):
#         result = super().button_validate()
#         for picking in self:
#             analytic = picking._get_warehouse_analytic_account()
#             if analytic:
#                 picking.move_ids.filtered(
#                     lambda m: not m.analytic_account_id
#                 ).write({'analytic_account_id': analytic.id})
#                 _logger.debug(
#                     'Warehouse analytic %s stamped on picking %s moves',
#                     analytic.name, picking.name,
#                 )
#         return result

# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import fields, models

_logger = logging.getLogger(__name__)


def _apply_analytic_to_journal_lines(env, analytic, valuation_accounts,
                                     label_hint=''):
    """
    Find recently posted stock journal entries (within last 15 seconds)
    and stamp the analytic on every line EXCEPT the stock valuation
    account lines (110100 Stock Valuation etc.).
    """
    if not analytic:
        return
    key = str(analytic.id)
    since = (datetime.now() - timedelta(seconds=15)).strftime(
        '%Y-%m-%d %H:%M:%S'
    )
    acc_moves = env['account.move'].search([
        ('move_type', '=', 'entry'),
        ('state', '=', 'posted'),
        ('create_date', '>=', since),
    ])
    for acc_move in acc_moves:
        for line in acc_move.line_ids.filtered(lambda l: l.account_id):
            if line.account_id.id in valuation_accounts:
                continue
            existing = line.analytic_distribution or {}
            if key not in existing:
                new_dist = dict(existing)
                new_dist[key] = 100.0
                try:
                    line.analytic_distribution = new_dist
                    _logger.debug(
                        'Analytic %s applied to %s line %s (%s) [%s]',
                        analytic.name, acc_move.name,
                        line.id, line.account_id.code, label_hint,
                    )
                except Exception as e:
                    _logger.warning(
                        'Could not set analytic on line %s: %s', line.id, e
                    )


class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        help='Analytic account inherited from the source warehouse.',
        index=True,
    )


class StockQuant(models.Model):
    """
    Intercept physical inventory adjustments (Operations > Physical Inventory).
    In Odoo 19 CE these go through stock.quant, not stock.picking.
    """
    _inherit = 'stock.quant'

    def _get_quant_analytic_info(self):
        """
        Return list of (analytic, valuation_account_ids_set) for every
        quant whose warehouse has an analytic account configured.
        """
        results = []
        for quant in self:
            wh = quant.location_id.warehouse_id
            if not wh or not wh.analytic_account_id:
                continue
            analytic = wh.analytic_account_id
            valuation_accounts = set()
            categ = quant.product_id.categ_id
            if hasattr(categ, 'property_stock_valuation_account_id'):
                acc = categ.property_stock_valuation_account_id
                if acc:
                    valuation_accounts.add(acc.id)
            results.append((analytic, valuation_accounts))
        return results

    def action_apply_inventory(self):
        """'Apply' button on a single Physical Inventory line."""
        info = self._get_quant_analytic_info()
        result = super().action_apply_inventory()
        for analytic, valuation_accounts in info:
            _apply_analytic_to_journal_lines(
                self.env, analytic, valuation_accounts,
                label_hint='action_apply_inventory',
            )
        return result

    def _apply_inventory(self, date=None):
        """
        Internal method called by action_apply_inventory.
        Odoo 19 CE passes a 'date' positional argument — we must accept it.
        """
        info = self._get_quant_analytic_info()
        # Pass date through correctly whether or not it was supplied
        if date is not None:
            result = super()._apply_inventory(date)
        else:
            result = super()._apply_inventory()
        for analytic, valuation_accounts in info:
            _apply_analytic_to_journal_lines(
                self.env, analytic, valuation_accounts,
                label_hint='_apply_inventory',
            )
        return result


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

    def _push_analytic_to_stock_journal_entries(self, analytic):
        """
        Push warehouse analytic onto stock valuation journal entries
        for receipts/deliveries — matches by picking name in account.move.ref.
        """
        if not analytic:
            return
        valuation_accounts = set()
        for move in self.move_ids:
            categ = move.product_id.categ_id
            if hasattr(categ, 'property_stock_valuation_account_id'):
                acc = categ.property_stock_valuation_account_id
                if acc:
                    valuation_accounts.add(acc.id)
        _apply_analytic_to_journal_lines(
            self.env, analytic, valuation_accounts,
            label_hint='picking_%s' % self.name,
        )

    def button_validate(self):
        result = super().button_validate()
        for picking in self:
            analytic = picking._get_warehouse_analytic_account()
            if not analytic:
                continue
            picking.move_ids.filtered(
                lambda m: not m.analytic_account_id
            ).write({'analytic_account_id': analytic.id})
            _logger.debug(
                'Warehouse analytic %s stamped on picking %s moves',
                analytic.name, picking.name,
            )
            picking._push_analytic_to_stock_journal_entries(analytic)
        return result