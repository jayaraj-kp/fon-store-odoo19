# # # # # -*- coding: utf-8 -*-
# # # # import logging
# # # # from odoo import fields, models
# # # #
# # # # _logger = logging.getLogger(__name__)
# # # #
# # # #
# # # # class StockMove(models.Model):
# # # #     _inherit = 'stock.move'
# # # #
# # # #     analytic_account_id = fields.Many2one(
# # # #         comodel_name='account.analytic.account',
# # # #         string='Analytic Account',
# # # #         help='Analytic account inherited from the source warehouse.',
# # # #         index=True,
# # # #     )
# # # #
# # # #
# # # # class StockPicking(models.Model):
# # # #     _inherit = 'stock.picking'
# # # #
# # # #     def _get_warehouse_analytic_account(self):
# # # #         wh = (
# # # #             self.location_id.warehouse_id
# # # #             or self.picking_type_id.warehouse_id
# # # #         )
# # # #         if wh and wh.analytic_account_id:
# # # #             return wh.analytic_account_id
# # # #         return False
# # # #
# # # #     def button_validate(self):
# # # #         result = super().button_validate()
# # # #         for picking in self:
# # # #             analytic = picking._get_warehouse_analytic_account()
# # # #             if analytic:
# # # #                 picking.move_ids.filtered(
# # # #                     lambda m: not m.analytic_account_id
# # # #                 ).write({'analytic_account_id': analytic.id})
# # # #                 _logger.debug(
# # # #                     'Warehouse analytic %s stamped on picking %s moves',
# # # #                     analytic.name, picking.name,
# # # #                 )
# # # #         return result
# # #
# # # # -*- coding: utf-8 -*-
# # # import logging
# # # from datetime import datetime, timedelta
# # # from odoo import fields, models
# # #
# # # _logger = logging.getLogger(__name__)
# # #
# # #
# # # def _apply_analytic_to_journal_lines(env, analytic, label_hint=''):
# # #     """
# # #     Find recently posted stock journal entries (within last 15 seconds)
# # #     and stamp the analytic on ALL lines including the stock valuation
# # #     account line.
# # #     """
# # #     if not analytic:
# # #         return
# # #     key = str(analytic.id)
# # #     since = (datetime.now() - timedelta(seconds=15)).strftime(
# # #         '%Y-%m-%d %H:%M:%S'
# # #     )
# # #     acc_moves = env['account.move'].search([
# # #         ('move_type', '=', 'entry'),
# # #         ('state', '=', 'posted'),
# # #         ('create_date', '>=', since),
# # #     ])
# # #     for acc_move in acc_moves:
# # #         for line in acc_move.line_ids.filtered(lambda l: l.account_id):
# # #             existing = line.analytic_distribution or {}
# # #             if key not in existing:
# # #                 new_dist = dict(existing)
# # #                 new_dist[key] = 100.0
# # #                 try:
# # #                     line.analytic_distribution = new_dist
# # #                     _logger.debug(
# # #                         'Analytic %s applied to %s line %s (%s) [%s]',
# # #                         analytic.name, acc_move.name,
# # #                         line.id, line.account_id.code, label_hint,
# # #                     )
# # #                 except Exception as e:
# # #                     _logger.warning(
# # #                         'Could not set analytic on line %s: %s', line.id, e
# # #                     )
# # #
# # #
# # # class StockMove(models.Model):
# # #     _inherit = 'stock.move'
# # #
# # #     analytic_account_id = fields.Many2one(
# # #         comodel_name='account.analytic.account',
# # #         string='Analytic Account',
# # #         help='Analytic account inherited from the source warehouse.',
# # #         index=True,
# # #     )
# # #
# # #
# # # class StockQuant(models.Model):
# # #     """
# # #     Intercept physical inventory adjustments (Operations > Physical Inventory).
# # #     In Odoo 19 CE these go through stock.quant, not stock.picking.
# # #     """
# # #     _inherit = 'stock.quant'
# # #
# # #     def _get_quant_analytic(self):
# # #         """
# # #         Return the analytic account for the first quant in self
# # #         whose warehouse has an analytic account configured.
# # #         """
# # #         for quant in self:
# # #             wh = quant.location_id.warehouse_id
# # #             if wh and wh.analytic_account_id:
# # #                 return wh.analytic_account_id
# # #         return False
# # #
# # #     def action_apply_inventory(self):
# # #         """'Apply' button on a single Physical Inventory line."""
# # #         analytic = self._get_quant_analytic()
# # #         result = super().action_apply_inventory()
# # #         _apply_analytic_to_journal_lines(
# # #             self.env, analytic, label_hint='action_apply_inventory',
# # #         )
# # #         return result
# # #
# # #     def _apply_inventory(self, date=None):
# # #         """
# # #         Internal method called by action_apply_inventory.
# # #         Odoo 19 CE passes a 'date' positional argument.
# # #         """
# # #         analytic = self._get_quant_analytic()
# # #         if date is not None:
# # #             result = super()._apply_inventory(date)
# # #         else:
# # #             result = super()._apply_inventory()
# # #         _apply_analytic_to_journal_lines(
# # #             self.env, analytic, label_hint='_apply_inventory',
# # #         )
# # #         return result
# # #
# # #
# # # class StockPicking(models.Model):
# # #     _inherit = 'stock.picking'
# # #
# # #     def _get_warehouse_analytic_account(self):
# # #         wh = (
# # #             self.location_id.warehouse_id
# # #             or self.picking_type_id.warehouse_id
# # #         )
# # #         if wh and wh.analytic_account_id:
# # #             return wh.analytic_account_id
# # #         return False
# # #
# # #     def _push_analytic_to_stock_journal_entries(self, analytic):
# # #         """
# # #         Push warehouse analytic onto ALL stock valuation journal entry
# # #         lines for receipts/deliveries.
# # #         """
# # #         _apply_analytic_to_journal_lines(
# # #             self.env, analytic,
# # #             label_hint='picking_%s' % self.name,
# # #         )
# # #
# # #     def button_validate(self):
# # #         result = super().button_validate()
# # #         for picking in self:
# # #             analytic = picking._get_warehouse_analytic_account()
# # #             if not analytic:
# # #                 continue
# # #             picking.move_ids.filtered(
# # #                 lambda m: not m.analytic_account_id
# # #             ).write({'analytic_account_id': analytic.id})
# # #             _logger.debug(
# # #                 'Warehouse analytic %s stamped on picking %s moves',
# # #                 analytic.name, picking.name,
# # #             )
# # #             picking._push_analytic_to_stock_journal_entries(analytic)
# # #         return result
# #
# # # -*- coding: utf-8 -*-
# # # -*- coding: utf-8 -*-
# # import logging
# # from datetime import datetime, timedelta
# # from odoo import fields, models
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # def _apply_analytic_to_journal_lines(env, analytic, label_hint=''):
# #     """
# #     Find recently posted stock journal entries (within last 15 seconds)
# #     and stamp the analytic on ALL lines including the stock valuation
# #     account line.
# #     """
# #     if not analytic:
# #         return
# #     key = str(analytic.id)
# #     since = (datetime.now() - timedelta(seconds=15)).strftime(
# #         '%Y-%m-%d %H:%M:%S'
# #     )
# #     acc_moves = env['account.move'].search([
# #         ('move_type', '=', 'entry'),
# #         ('state', '=', 'posted'),
# #         ('create_date', '>=', since),
# #     ])
# #     for acc_move in acc_moves:
# #         for line in acc_move.line_ids.filtered(lambda l: l.account_id):
# #             existing = line.analytic_distribution or {}
# #             if key not in existing:
# #                 new_dist = dict(existing)
# #                 new_dist[key] = 100.0
# #                 try:
# #                     line.analytic_distribution = new_dist
# #                     _logger.debug(
# #                         'Analytic %s applied to %s line %s (%s) [%s]',
# #                         analytic.name, acc_move.name,
# #                         line.id, line.account_id.code, label_hint,
# #                     )
# #                 except Exception as e:
# #                     _logger.warning(
# #                         'Could not set analytic on line %s: %s', line.id, e
# #                     )
# #
# #
# # def _apply_analytic_to_move_direct(env, analytic, move, label_hint=''):
# #     """
# #     Directly stamp analytic on a specific account.move (more precise than
# #     the time-window approach — use this when we have the exact move record).
# #     """
# #     if not analytic or not move:
# #         return
# #     key = str(analytic.id)
# #     for line in move.line_ids.filtered(lambda l: l.account_id):
# #         existing = line.analytic_distribution or {}
# #         if key not in existing:
# #             new_dist = dict(existing)
# #             new_dist[key] = 100.0
# #             try:
# #                 line.sudo().with_context(
# #                     check_move_validity=False,
# #                     skip_account_move_synchronization=True,
# #                 ).analytic_distribution = new_dist
# #                 _logger.debug(
# #                     'Analytic %s applied to %s line %s (%s) [%s]',
# #                     analytic.name, move.name,
# #                     line.id, line.account_id.code, label_hint,
# #                 )
# #             except Exception as e:
# #                 _logger.warning(
# #                     'Could not set analytic on line %s: %s', line.id, e
# #                 )
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
# # _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
# #
# #
# # def _get_user_warehouse(user):
# #     """Resolve the user's default warehouse across different Odoo versions."""
# #     for fname in _WAREHOUSE_FIELDS:
# #         if fname in user._fields:
# #             return getattr(user, fname, False)
# #     return False
# #
# #
# # class StockScrap(models.Model):
# #     """
# #     Intercept scrap validation (Operations > Scrap) so the warehouse
# #     analytic account is stamped on the generated STJ journal entry.
# #
# #     Warehouse resolution order (mirrors sale/purchase logic):
# #       1. Current user's default warehouse analytic  ← PRIMARY (same as SO/PO)
# #       2. scrap.picking_type_id.warehouse_id         ← fallback
# #       3. scrap.location_id.warehouse_id             ← fallback
# #       4. scrap.picking_id.location_id.warehouse_id  ← last resort
# #     """
# #     _inherit = 'stock.scrap'
# #
# #     def _get_scrap_analytic(self):
# #         # 1. User's default warehouse — same source as sale/purchase orders
# #         wh = _get_user_warehouse(self.env.user)
# #         if wh and getattr(wh, 'analytic_account_id', False):
# #             _logger.debug(
# #                 'Scrap analytic STRATEGY 1 (user default wh): user[%s] → wh[%s] → %s',
# #                 self.env.user.name, wh.name, wh.analytic_account_id.name,
# #             )
# #             return wh.analytic_account_id
# #
# #         for scrap in self:
# #             # 2. Scrap operation type warehouse
# #             wh = getattr(
# #                 getattr(scrap, 'picking_type_id', False),
# #                 'warehouse_id', False,
# #             )
# #             if wh and getattr(wh, 'analytic_account_id', False):
# #                 _logger.debug(
# #                     'Scrap analytic STRATEGY 2 (picking_type): scrap[%s] → wh[%s] → %s',
# #                     scrap.name, wh.name, wh.analytic_account_id.name,
# #                 )
# #                 return wh.analytic_account_id
# #
# #             # 3. Source stock location warehouse
# #             wh = getattr(scrap.location_id, 'warehouse_id', False)
# #             if wh and getattr(wh, 'analytic_account_id', False):
# #                 _logger.debug(
# #                     'Scrap analytic STRATEGY 3 (location): scrap[%s] → wh[%s] → %s',
# #                     scrap.name, wh.name, wh.analytic_account_id.name,
# #                 )
# #                 return wh.analytic_account_id
# #
# #             # 4. Linked transfer warehouse
# #             picking = getattr(scrap, 'picking_id', False)
# #             if picking:
# #                 wh = getattr(picking.location_id, 'warehouse_id', False)
# #                 if wh and getattr(wh, 'analytic_account_id', False):
# #                     _logger.debug(
# #                         'Scrap analytic STRATEGY 4 (picking): scrap[%s] → wh[%s] → %s',
# #                         scrap.name, wh.name, wh.analytic_account_id.name,
# #                     )
# #                     return wh.analytic_account_id
# #
# #         _logger.warning('Scrap analytic: no match for user[%s]', self.env.user.name)
# #         return False
# #
# #     def action_validate(self):
# #         """
# #         Intercept scrap confirmation.
# #
# #         We capture the analytic BEFORE calling super() (while we still
# #         have location/picking context), then apply it AFTER so that
# #         the STJ journal entry already exists and is posted.
# #         """
# #         # Resolve analytic per scrap record before validation clears context
# #         scrap_analytics = {scrap.id: scrap._get_scrap_analytic() for scrap in self}
# #
# #         result = super().action_validate()
# #
# #         for scrap in self:
# #             analytic = scrap_analytics.get(scrap.id)
# #             if not analytic:
# #                 _logger.warning(
# #                     'StockScrap: no analytic found for scrap %s', scrap.name
# #                 )
# #                 continue
# #
# #             # Prefer the direct move_id on the scrap (most precise)
# #             scrap_move = getattr(scrap, 'move_id', False)
# #             if scrap_move and scrap_move.account_move_ids:
# #                 for acc_move in scrap_move.account_move_ids:
# #                     _apply_analytic_to_move_direct(
# #                         self.env, analytic, acc_move,
# #                         label_hint='scrap_%s' % scrap.name,
# #                     )
# #                 _logger.debug(
# #                     'Scrap analytic %s applied via move_id for %s',
# #                     analytic.name, scrap.name,
# #                 )
# #             else:
# #                 # Fallback: time-window search (covers edge cases)
# #                 _apply_analytic_to_journal_lines(
# #                     self.env, analytic,
# #                     label_hint='scrap_%s' % scrap.name,
# #                 )
# #                 _logger.debug(
# #                     'Scrap analytic %s applied via time-window for %s',
# #                     analytic.name, scrap.name,
# #                 )
# #
# #         return result
# #
# #
# # class StockQuant(models.Model):
# #     """
# #     Intercept physical inventory adjustments (Operations > Physical Inventory).
# #     In Odoo 19 CE these go through stock.quant, not stock.picking.
# #     """
# #     _inherit = 'stock.quant'
# #
# #     def _get_quant_analytic(self):
# #         """
# #         Return the analytic account for the first quant in self
# #         whose warehouse has an analytic account configured.
# #         """
# #         for quant in self:
# #             wh = quant.location_id.warehouse_id
# #             if wh and wh.analytic_account_id:
# #                 return wh.analytic_account_id
# #         return False
# #
# #     def action_apply_inventory(self):
# #         """'Apply' button on a single Physical Inventory line."""
# #         analytic = self._get_quant_analytic()
# #         result = super().action_apply_inventory()
# #         _apply_analytic_to_journal_lines(
# #             self.env, analytic, label_hint='action_apply_inventory',
# #         )
# #         return result
# #
# #     def _apply_inventory(self, date=None):
# #         """
# #         Internal method called by action_apply_inventory.
# #         Odoo 19 CE passes a 'date' positional argument.
# #         """
# #         analytic = self._get_quant_analytic()
# #         if date is not None:
# #             result = super()._apply_inventory(date)
# #         else:
# #             result = super()._apply_inventory()
# #         _apply_analytic_to_journal_lines(
# #             self.env, analytic, label_hint='_apply_inventory',
# #         )
# #         return result
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
# #     def _push_analytic_to_stock_journal_entries(self, analytic):
# #         """
# #         Push warehouse analytic onto ALL stock valuation journal entry
# #         lines for receipts/deliveries.
# #         """
# #         _apply_analytic_to_journal_lines(
# #             self.env, analytic,
# #             label_hint='picking_%s' % self.name,
# #         )
# #
# #     def button_validate(self):
# #         result = super().button_validate()
# #         for picking in self:
# #             analytic = picking._get_warehouse_analytic_account()
# #             if not analytic:
# #                 continue
# #             picking.move_ids.filtered(
# #                 lambda m: not m.analytic_account_id
# #             ).write({'analytic_account_id': analytic.id})
# #             _logger.debug(
# #                 'Warehouse analytic %s stamped on picking %s moves',
# #                 analytic.name, picking.name,
# #             )
# #             picking._push_analytic_to_stock_journal_entries(analytic)
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
#     if not analytic:
#         return
#     key = str(analytic.id)
#     since = (datetime.now() - timedelta(seconds=15)).strftime('%Y-%m-%d %H:%M:%S')
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
#                 except Exception as e:
#                     _logger.warning('Could not set analytic on line %s: %s', line.id, e)
#
#
# def _apply_analytic_to_move_direct(env, analytic, move, label_hint=''):
#     if not analytic or not move:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             try:
#                 line.sudo().with_context(
#                     check_move_validity=False,
#                     skip_account_move_synchronization=True,
#                 ).analytic_distribution = new_dist
#                 _logger.debug(
#                     'Analytic %s applied to %s line %s [%s]',
#                     analytic.name, move.name, line.id, label_hint,
#                 )
#             except Exception as e:
#                 _logger.warning('Could not set analytic on line %s: %s', line.id, e)
#
#
# def _apply_analytic_to_move_lines(move, analytic):
#     """Apply analytic distribution to all lines of an account.move."""
#     if not move or not analytic:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             try:
#                 line.sudo().with_context(
#                     check_move_validity=False,
#                     skip_account_move_synchronization=True,
#                 ).analytic_distribution = new_dist
#                 _logger.debug(
#                     'STJ analytic %s applied to %s line %s',
#                     analytic.name, move.name, line.id,
#                 )
#             except Exception as e:
#                 _logger.warning(
#                     'Could not apply analytic to STJ line %s: %s', line.id, e
#                 )
#
#
# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     analytic_account_id = fields.Many2one(
#         comodel_name='account.analytic.account',
#         string='Analytic Account',
#         index=True,
#     )
#
#
# _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
#
#
# def _get_user_warehouse(user):
#     for fname in _WAREHOUSE_FIELDS:
#         if fname in user._fields:
#             return getattr(user, fname, False)
#     return False
#
#
# class StockScrap(models.Model):
#     _inherit = 'stock.scrap'
#
#     def _get_scrap_analytic(self):
#         wh = _get_user_warehouse(self.env.user)
#         if wh and getattr(wh, 'analytic_account_id', False):
#             return wh.analytic_account_id
#         for scrap in self:
#             wh = getattr(getattr(scrap, 'picking_type_id', False), 'warehouse_id', False)
#             if wh and getattr(wh, 'analytic_account_id', False):
#                 return wh.analytic_account_id
#             wh = getattr(scrap.location_id, 'warehouse_id', False)
#             if wh and getattr(wh, 'analytic_account_id', False):
#                 return wh.analytic_account_id
#         return False
#
#     def action_validate(self):
#         scrap_analytics = {scrap.id: scrap._get_scrap_analytic() for scrap in self}
#         result = super().action_validate()
#         for scrap in self:
#             analytic = scrap_analytics.get(scrap.id)
#             if not analytic:
#                 continue
#             scrap_move = getattr(scrap, 'move_id', False)
#             if scrap_move and scrap_move.account_move_ids:
#                 for acc_move in scrap_move.account_move_ids:
#                     _apply_analytic_to_move_direct(self.env, analytic, acc_move, 'scrap')
#             else:
#                 _apply_analytic_to_journal_lines(self.env, analytic, 'scrap')
#         return result
#
#
# class StockQuant(models.Model):
#     _inherit = 'stock.quant'
#
#     def _get_quant_analytic(self):
#         for quant in self:
#             wh = quant.location_id.warehouse_id
#             if wh and wh.analytic_account_id:
#                 return wh.analytic_account_id
#         return False
#
#     def action_apply_inventory(self):
#         analytic = self._get_quant_analytic()
#         result = super().action_apply_inventory()
#         _apply_analytic_to_journal_lines(self.env, analytic, 'action_apply_inventory')
#         return result
#
#     def _apply_inventory(self, date=None):
#         analytic = self._get_quant_analytic()
#         if date is not None:
#             result = super()._apply_inventory(date)
#         else:
#             result = super()._apply_inventory()
#         _apply_analytic_to_journal_lines(self.env, analytic, '_apply_inventory')
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
#     def button_validate(self):
#         result = super().button_validate()
#         for picking in self:
#             analytic = picking._get_warehouse_analytic_account()
#             if not analytic:
#                 continue
#             picking.move_ids.filtered(
#                 lambda m: not m.analytic_account_id
#             ).write({'analytic_account_id': analytic.id})
#             _apply_analytic_to_journal_lines(
#                 self.env, analytic, 'picking_%s' % picking.name
#             )
#         return result
#
#     def _create_delivery_valuation_entry(self):
#         """Apply warehouse analytic to Anglo-Saxon delivery STJ entries."""
#         res = super()._create_delivery_valuation_entry()
#         for picking in self:
#             analytic = picking._get_warehouse_analytic_account()
#             if not analytic:
#                 continue
#             for entry in picking.delivery_journal_entry_ids:
#                 _apply_analytic_to_move_lines(entry, analytic)
#                 _logger.info(
#                     'STJ delivery analytic %s applied to %s',
#                     analytic.name, entry.name
#                 )
#         return res
#
#     def _create_receipt_valuation_entry(self):
#         """Apply warehouse analytic to Anglo-Saxon receipt STJ entries."""
#         res = super()._create_receipt_valuation_entry()
#         for picking in self:
#             analytic = picking._get_warehouse_analytic_account()
#             if not analytic:
#                 continue
#             for entry in picking.receipt_journal_entry_ids:
#                 _apply_analytic_to_move_lines(entry, analytic)
#                 _logger.info(
#                     'STJ receipt analytic %s applied to %s',
#                     analytic.name, entry.name
#                 )
#         return res
# -*- coding: utf-8 -*-
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

FIX (v2):
  The _action_done fallback was incorrectly processing POS pickings because
  picking.pos_order_id is not yet set when _action_done fires during POS sync.
  The skip check `if picking.pos_order_id: continue` therefore never triggered.

  Solution: Apply the warehouse analytic immediately after creating the delivery
  valuation entry, reading the warehouse from picking.picking_type_id.warehouse_id
  instead of env.user — which may be Administrator with a different default warehouse.
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

    # Fallback: match by source location
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
                    # Apply analytic immediately using picking's own warehouse
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
        programmatically (e.g. scheduler, internal operations).

        NOTE: The original `if picking.pos_order_id: continue` check does NOT
        reliably skip POS pickings because pos_order_id is not yet set when
        _action_done fires during POS sync_from_ui. Instead we check the
        picking_type_code name for POS patterns as an additional guard,
        but we always apply analytic from picking's warehouse (not env.user)
        so even if a POS picking slips through here the analytic will be correct.
        """
        res = super()._action_done()
        for picking in self:
            if picking.state != 'done':
                continue
            if picking.picking_type_code != 'outgoing':
                continue
            if picking.delivery_journal_entry_ids:
                continue

            # Skip if this is a POS picking that will be handled by
            # _process_saved_order → _create_anglo_saxon_pos_delivery_entries
            # Check both pos_order_id (may be set by now) and picking_type name
            if picking.pos_order_id:
                _logger.debug(
                    "Anglo-Saxon _action_done: skipping POS picking '%s'"
                    " (pos_order_id=%s)",
                    picking.name, picking.pos_order_id.name,
                )
                continue

            try:
                picking._create_delivery_valuation_entry()

                # Apply analytic from picking's own warehouse immediately
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