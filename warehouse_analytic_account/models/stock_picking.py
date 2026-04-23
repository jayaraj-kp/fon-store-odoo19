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
        Push warehouse analytic distribution onto the stock valuation
        journal entries linked to this picking.

        In Odoo 19 CE, stock.valuation.layer does not exist.
        We find the journal entries by searching account.move with:
          - journal = 'Inventory Valuation' type journal (stock_journal)
          - ref matching the picking name or move description

        The stock valuation account line is skipped — only the counterpart
        line (Stock Interim / Inventory Loss) gets the analytic tag.
        """
        if not analytic:
            return
        key = str(analytic.id)

        # Collect valuation accounts to skip (these should NOT get analytic)
        valuation_accounts = set()
        for move in self.move_ids:
            acc = move.product_id.categ_id.property_stock_valuation_account_id
            if acc:
                valuation_accounts.add(acc.id)

        # Find stock journal entries linked to this picking.
        # In Odoo 19 CE, inventory valuation journal entries use the
        # picking name or move description in their ref field.
        acc_moves = self.env['account.move'].search([
            ('ref', 'like', self.name),
            ('move_type', '=', 'entry'),
            ('state', '=', 'posted'),
        ])

        if not acc_moves:
            # Fallback: also try matching on individual move descriptions
            move_names = self.move_ids.mapped('name')
            if move_names:
                acc_moves = self.env['account.move'].search([
                    ('ref', 'in', move_names),
                    ('move_type', '=', 'entry'),
                    ('state', '=', 'posted'),
                ])

        for acc_move in acc_moves:
            for line in acc_move.line_ids.filtered(lambda l: l.account_id):
                # Skip stock valuation account — only tag counterpart lines
                if line.account_id.id in valuation_accounts:
                    continue
                existing = line.analytic_distribution or {}
                if key not in existing:
                    new_dist = dict(existing)
                    new_dist[key] = 100.0
                    try:
                        line.analytic_distribution = new_dist
                        _logger.debug(
                            'Stock analytic %s → %s line %s (%s)',
                            analytic.name, acc_move.name,
                            line.id, line.account_id.code,
                        )
                    except Exception as e:
                        _logger.warning(
                            'Could not set analytic on stock journal line %s: %s',
                            line.id, e,
                        )

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
            # Push analytic into the stock valuation journal entry lines
            picking._push_analytic_to_stock_journal_entries(analytic)
        return result