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
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


def _get_analytic_from_picking(picking):
    """
    Resolve the correct analytic account from the picking itself,
    NOT from env.user.

    Priority:
    1. picking.picking_type_id → warehouse_id → analytic_account_id
       (Most reliable — the picking carries its own warehouse reference)
    2. Search warehouses by matching picking's source location
       (Fallback if picking_type has no warehouse linked)

    Why NOT env.user:
    - POS pickings are validated by the POS session close process,
      which runs as a background/admin user whose default warehouse
      may differ from the actual POS warehouse.
    - Stock transfers validated via schedulers face the same issue.
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

        The analytic is resolved from the picking's own picking_type_id
        → warehouse_id, NOT from env.user — because POS pickings are
        validated by a background process user whose default warehouse
        may be completely different from the actual picking's warehouse.
        """
        result = super().button_validate()
        for picking in self:
            if picking.state != 'done':
                continue
            analytic = _get_analytic_from_picking(picking)
            if not analytic:
                continue

            # Apply to receipt journal entries (purchase/incoming)
            for entry in picking.receipt_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='receipt_%s' % picking.name,
                )

            # Apply to delivery journal entries (sales/outgoing)
            for entry in picking.delivery_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='delivery_%s' % picking.name,
                )
        return result

    def _action_done(self):
        """
        Secondary hook for pickings validated programmatically
        (e.g. via scheduler, POS session close, or internal transfers)
        rather than through button_validate.

        Applies the same warehouse analytic logic using the picking's
        own warehouse, not env.user.
        """
        result = super()._action_done()
        for picking in self:
            if picking.state != 'done':
                continue
            analytic = _get_analytic_from_picking(picking)
            if not analytic:
                continue

            # Apply to receipt journal entries
            for entry in picking.receipt_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='receipt_action_done_%s' % picking.name,
                )

            # Apply to delivery journal entries
            for entry in picking.delivery_journal_entry_ids:
                _apply_analytic_to_move(
                    entry, analytic,
                    label='delivery_action_done_%s' % picking.name,
                )
        return result