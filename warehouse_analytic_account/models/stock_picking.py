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
from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        help='Analytic account inherited from the source warehouse.',
        index=True,
    )

    def _push_analytic_to_svl_journal_lines(self, analytic):
        """
        After a stock move creates its SVL journal entry, push the warehouse
        analytic distribution onto the counterpart journal lines.
        The stock valuation account line is intentionally skipped
        (standard Odoo convention — only the interim/expense line gets analytic).
        """
        if not analytic:
            return
        key = str(analytic.id)
        for move in self:
            # Find SVL account moves linked to this stock move
            svl_moves = move.stock_valuation_layer_ids.mapped('account_move_id')
            if not svl_moves:
                continue
            # Get the stock valuation account to skip it
            valuation_account = (
                move.product_id.categ_id.property_stock_valuation_account_id
            )
            for acc_move in svl_moves:
                for line in acc_move.line_ids.filtered(lambda l: l.account_id):
                    # Skip the pure stock valuation account line
                    if valuation_account and line.account_id == valuation_account:
                        continue
                    existing = line.analytic_distribution or {}
                    if key not in existing:
                        new_dist = dict(existing)
                        new_dist[key] = 100.0
                        try:
                            line.analytic_distribution = new_dist
                            _logger.debug(
                                'SVL analytic %s → move %s line %s (%s)',
                                analytic.name, acc_move.name,
                                line.id, line.account_id.code,
                            )
                        except Exception as e:
                            _logger.warning(
                                'Could not set analytic on SVL line %s: %s',
                                line.id, e,
                            )


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
            # Stamp analytic_account_id on stock moves (existing behaviour)
            picking.move_ids.filtered(
                lambda m: not m.analytic_account_id
            ).write({'analytic_account_id': analytic.id})
            _logger.debug(
                'Warehouse analytic %s stamped on picking %s moves',
                analytic.name, picking.name,
            )
            # NEW: also push analytic into the SVL journal entry lines
            # so inventory adjustment journal entries show the correct
            # analytic distribution (FS Kondotty, etc.)
            picking.move_ids._push_analytic_to_svl_journal_lines(analytic)
        return result