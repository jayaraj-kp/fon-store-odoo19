# # # -*- coding: utf-8 -*-
# # import logging
# # from odoo import fields, models
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class StockMove(models.Model):
# #     _inherit = 'stock.move'
# #
# #     analytic_account_id = fields.Many2one(
# #         comodel_name='account.analytic.account',
# #         string='Analytic Account',
# #         help='Analytic account inherited from the source warehouse.',
# #         index=True,
# #     )
# #
# #
# # class StockPicking(models.Model):
# #     _inherit = 'stock.picking'
# #
# #     def _get_warehouse_analytic_account(self):
# #         wh = (
# #             self.location_id.warehouse_id
# #             or self.picking_type_id.warehouse_id
# #         )
# #         if wh and wh.analytic_account_id:
# #             return wh.analytic_account_id
# #         return False
# #
# #     def button_validate(self):
# #         result = super().button_validate()
# #         for picking in self:
# #             analytic = picking._get_warehouse_analytic_account()
# #             if analytic:
# #                 picking.move_ids.filtered(
# #                     lambda m: not m.analytic_account_id
# #                 ).write({'analytic_account_id': analytic.id})
# #                 _logger.debug(
# #                     'Warehouse analytic %s stamped on picking %s moves',
# #                     analytic.name, picking.name,
# #                 )
# #         return result
#
# # -*- coding: utf-8 -*-
# import logging
# from datetime import datetime, timedelta
# from odoo import fields, models
#
# _logger = logging.getLogger(__name__)
#
#
# def _apply_analytic_to_journal_lines(env, analytic, label_hint=''):
#     """
#     Find recently posted stock journal entries (within last 15 seconds)
#     and stamp the analytic on ALL lines including the stock valuation
#     account line.
#     """
#     if not analytic:
#         return
#     key = str(analytic.id)
#     since = (datetime.now() - timedelta(seconds=15)).strftime(
#         '%Y-%m-%d %H:%M:%S'
#     )
#     acc_moves = env['account.move'].search([
#         ('move_type', '=', 'entry'),
#         ('state', '=', 'posted'),
#         ('create_date', '>=', since),
#     ])
#     for acc_move in acc_moves:
#         for line in acc_move.line_ids.filtered(lambda l: l.account_id):
#             existing = line.analytic_distribution or {}
#             if key not in existing:
#                 new_dist = dict(existing)
#                 new_dist[key] = 100.0
#                 try:
#                     line.analytic_distribution = new_dist
#                     _logger.debug(
#                         'Analytic %s applied to %s line %s (%s) [%s]',
#                         analytic.name, acc_move.name,
#                         line.id, line.account_id.code, label_hint,
#                     )
#                 except Exception as e:
#                     _logger.warning(
#                         'Could not set analytic on line %s: %s', line.id, e
#                     )
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
# class StockQuant(models.Model):
#     """
#     Intercept physical inventory adjustments (Operations > Physical Inventory).
#     In Odoo 19 CE these go through stock.quant, not stock.picking.
#     """
#     _inherit = 'stock.quant'
#
#     def _get_quant_analytic(self):
#         """
#         Return the analytic account for the first quant in self
#         whose warehouse has an analytic account configured.
#         """
#         for quant in self:
#             wh = quant.location_id.warehouse_id
#             if wh and wh.analytic_account_id:
#                 return wh.analytic_account_id
#         return False
#
#     def action_apply_inventory(self):
#         """'Apply' button on a single Physical Inventory line."""
#         analytic = self._get_quant_analytic()
#         result = super().action_apply_inventory()
#         _apply_analytic_to_journal_lines(
#             self.env, analytic, label_hint='action_apply_inventory',
#         )
#         return result
#
#     def _apply_inventory(self, date=None):
#         """
#         Internal method called by action_apply_inventory.
#         Odoo 19 CE passes a 'date' positional argument.
#         """
#         analytic = self._get_quant_analytic()
#         if date is not None:
#             result = super()._apply_inventory(date)
#         else:
#             result = super()._apply_inventory()
#         _apply_analytic_to_journal_lines(
#             self.env, analytic, label_hint='_apply_inventory',
#         )
#         return result
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
#     def _push_analytic_to_stock_journal_entries(self, analytic):
#         """
#         Push warehouse analytic onto ALL stock valuation journal entry
#         lines for receipts/deliveries.
#         """
#         _apply_analytic_to_journal_lines(
#             self.env, analytic,
#             label_hint='picking_%s' % self.name,
#         )
#
#     def button_validate(self):
#         result = super().button_validate()
#         for picking in self:
#             analytic = picking._get_warehouse_analytic_account()
#             if not analytic:
#                 continue
#             picking.move_ids.filtered(
#                 lambda m: not m.analytic_account_id
#             ).write({'analytic_account_id': analytic.id})
#             _logger.debug(
#                 'Warehouse analytic %s stamped on picking %s moves',
#                 analytic.name, picking.name,
#             )
#             picking._push_analytic_to_stock_journal_entries(analytic)
#         return result

# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from odoo import fields, models

_logger = logging.getLogger(__name__)


def _apply_analytic_to_journal_lines(env, analytic, label_hint=''):
    """
    Find recently posted stock journal entries (within last 15 seconds)
    and stamp the analytic on ALL lines including the stock valuation
    account line.
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


def _apply_analytic_to_move_direct(env, analytic, move, label_hint=''):
    """
    Directly stamp analytic on a specific account.move (more precise than
    the time-window approach — use this when we have the exact move record).
    """
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
                    'Analytic %s applied to %s line %s (%s) [%s]',
                    analytic.name, move.name,
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


class StockScrap(models.Model):
    """
    Intercept scrap validation (Operations > Scrap) so the warehouse
    analytic account is stamped on the generated STJ journal entry.

    Warehouse resolution order:
      1. scrap.location_id.warehouse_id          (source stock location)
      2. scrap.picking_type_id.warehouse_id       (scrap operation type)
      3. scrap.picking_id.location_id.warehouse_id (linked picking, if any)
    """
    _inherit = 'stock.scrap'

    def _get_scrap_analytic(self):
        for scrap in self:
            # 1. Source location warehouse
            wh = getattr(scrap.location_id, 'warehouse_id', False)
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id

            # 2. Scrap operation type warehouse
            wh = getattr(
                getattr(scrap, 'picking_type_id', False),
                'warehouse_id', False,
            )
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id

            # 3. Linked transfer warehouse (if scrap was done from a picking)
            picking = getattr(scrap, 'picking_id', False)
            if picking:
                wh = getattr(picking.location_id, 'warehouse_id', False)
                if wh and getattr(wh, 'analytic_account_id', False):
                    return wh.analytic_account_id

        return False

    def action_validate(self):
        """
        Intercept scrap confirmation.

        We capture the analytic BEFORE calling super() (while we still
        have location/picking context), then apply it AFTER so that
        the STJ journal entry already exists and is posted.
        """
        # Resolve analytic per scrap record before validation clears context
        scrap_analytics = {scrap.id: scrap._get_scrap_analytic() for scrap in self}

        result = super().action_validate()

        for scrap in self:
            analytic = scrap_analytics.get(scrap.id)
            if not analytic:
                _logger.warning(
                    'StockScrap: no analytic found for scrap %s', scrap.name
                )
                continue

            # Prefer the direct move_id on the scrap (most precise)
            scrap_move = getattr(scrap, 'move_id', False)
            if scrap_move and scrap_move.account_move_ids:
                for acc_move in scrap_move.account_move_ids:
                    _apply_analytic_to_move_direct(
                        self.env, analytic, acc_move,
                        label_hint='scrap_%s' % scrap.name,
                    )
                _logger.debug(
                    'Scrap analytic %s applied via move_id for %s',
                    analytic.name, scrap.name,
                )
            else:
                # Fallback: time-window search (covers edge cases)
                _apply_analytic_to_journal_lines(
                    self.env, analytic,
                    label_hint='scrap_%s' % scrap.name,
                )
                _logger.debug(
                    'Scrap analytic %s applied via time-window for %s',
                    analytic.name, scrap.name,
                )

        return result


class StockQuant(models.Model):
    """
    Intercept physical inventory adjustments (Operations > Physical Inventory).
    In Odoo 19 CE these go through stock.quant, not stock.picking.
    """
    _inherit = 'stock.quant'

    def _get_quant_analytic(self):
        """
        Return the analytic account for the first quant in self
        whose warehouse has an analytic account configured.
        """
        for quant in self:
            wh = quant.location_id.warehouse_id
            if wh and wh.analytic_account_id:
                return wh.analytic_account_id
        return False

    def action_apply_inventory(self):
        """'Apply' button on a single Physical Inventory line."""
        analytic = self._get_quant_analytic()
        result = super().action_apply_inventory()
        _apply_analytic_to_journal_lines(
            self.env, analytic, label_hint='action_apply_inventory',
        )
        return result

    def _apply_inventory(self, date=None):
        """
        Internal method called by action_apply_inventory.
        Odoo 19 CE passes a 'date' positional argument.
        """
        analytic = self._get_quant_analytic()
        if date is not None:
            result = super()._apply_inventory(date)
        else:
            result = super()._apply_inventory()
        _apply_analytic_to_journal_lines(
            self.env, analytic, label_hint='_apply_inventory',
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
        Push warehouse analytic onto ALL stock valuation journal entry
        lines for receipts/deliveries.
        """
        _apply_analytic_to_journal_lines(
            self.env, analytic,
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