# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
#
#
# class StockPickingType(models.Model):
#     _inherit = 'stock.picking.type'
#
#     wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
#     wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')
#
#     @api.depends('code', 'warehouse_id', 'default_location_src_id', 'default_location_dest_id')
#     def _compute_wh_transfer_counts(self):
#         Picking = self.env['stock.picking']
#         all_wh_ids = self.env['stock.warehouse'].search([]).ids
#
#         for pt in self:
#             # Only Internal Transfer cards get badges
#             if pt.code != 'internal' or not pt.warehouse_id:
#                 pt.wh_to_send_count = 0
#                 pt.wh_to_accept_count = 0
#                 continue
#
#             wh_id = pt.warehouse_id.id
#             # All internal locations belonging to THIS warehouse
#             own_locs = self.env['stock.location'].search([
#                 ('warehouse_id', '=', wh_id),
#                 ('usage', '=', 'internal'),
#             ])
#             # All internal locations belonging to OTHER warehouses
#             other_ids = [w for w in all_wh_ids if w != wh_id]
#             other_locs = self.env['stock.location'].search([
#                 ('warehouse_id', 'in', other_ids),
#                 ('usage', '=', 'internal'),
#             ]) if other_ids else self.env['stock.location']
#
#             if not own_locs or not other_locs:
#                 pt.wh_to_send_count = 0
#                 pt.wh_to_accept_count = 0
#                 continue
#
#             # To Send: going OUT from this warehouse to another
#             pt.wh_to_send_count = Picking.search_count([
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_id', 'in', own_locs.ids),
#                 ('location_dest_id', 'in', other_locs.ids),
#             ])
#             # To Accept: coming IN to this warehouse from another
#             pt.wh_to_accept_count = Picking.search_count([
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_dest_id', 'in', own_locs.ids),
#                 ('location_id', 'in', other_locs.ids),
#             ])
#
#     def action_open_to_send(self):
#         """Open outgoing cross-warehouse transfers for this picking type's warehouse."""
#         self.ensure_one()
#         all_wh_ids = self.env['stock.warehouse'].search([]).ids
#         wh_id = self.warehouse_id.id
#
#         own_locs = self.env['stock.location'].search([
#             ('warehouse_id', '=', wh_id),
#             ('usage', '=', 'internal'),
#         ])
#         other_ids = [w for w in all_wh_ids if w != wh_id]
#         other_locs = self.env['stock.location'].search([
#             ('warehouse_id', 'in', other_ids),
#             ('usage', '=', 'internal'),
#         ]) if other_ids else self.env['stock.location']
#
#         return {
#             'name': 'To Send',
#             'type': 'ir.actions.act_window',
#             'res_model': 'stock.picking',
#             'view_mode': 'list,form',
#             'domain': [
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_id', 'in', own_locs.ids),
#                 ('location_dest_id', 'in', other_locs.ids),
#             ],
#         }
#
#     def action_open_to_accept(self):
#         """Open incoming cross-warehouse transfers for this picking type's warehouse."""
#         self.ensure_one()
#         all_wh_ids = self.env['stock.warehouse'].search([]).ids
#         wh_id = self.warehouse_id.id
#
#         own_locs = self.env['stock.location'].search([
#             ('warehouse_id', '=', wh_id),
#             ('usage', '=', 'internal'),
#         ])
#         other_ids = [w for w in all_wh_ids if w != wh_id]
#         other_locs = self.env['stock.location'].search([
#             ('warehouse_id', 'in', other_ids),
#             ('usage', '=', 'internal'),
#         ]) if other_ids else self.env['stock.location']
#
#         return {
#             'name': 'To Accept',
#             'type': 'ir.actions.act_window',
#             'res_model': 'stock.picking',
#             'view_mode': 'list,form',
#             'domain': [
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_dest_id', 'in', own_locs.ids),
#                 ('location_id', 'in', other_locs.ids),
#             ],
#         }
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     send_accept_label = fields.Char(
#         string='Send/Accept',
#         compute='_compute_send_accept_label',
#         store=False,
#     )
#
#     @api.depends('location_id.warehouse_id', 'location_dest_id.warehouse_id', 'picking_type_code')
#     def _compute_send_accept_label(self):
#         for pick in self:
#             if pick.picking_type_code != 'internal':
#                 pick.send_accept_label = False
#                 continue
#             src_wh = pick.location_id.warehouse_id
#             dst_wh = pick.location_dest_id.warehouse_id
#             if src_wh and dst_wh and src_wh != dst_wh:
#                 pick.send_accept_label = 'To Send'
#             else:
#                 pick.send_accept_label = False
# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
    wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')

    @api.depends('code', 'warehouse_id', 'default_location_src_id', 'default_location_dest_id')
    def _compute_wh_transfer_counts(self):
        Picking = self.env['stock.picking']
        all_wh_ids = self.env['stock.warehouse'].search([]).ids

        for pt in self:
            # Only Internal Transfer cards get badges
            if pt.code != 'internal' or not pt.warehouse_id:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            wh_id = pt.warehouse_id.id
            # All internal locations belonging to THIS warehouse
            own_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh_id),
                ('usage', '=', 'internal'),
            ])
            # All internal locations belonging to OTHER warehouses
            other_ids = [w for w in all_wh_ids if w != wh_id]
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', 'in', other_ids),
                ('usage', '=', 'internal'),
            ]) if other_ids else self.env['stock.location']

            if not own_locs or not other_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            # To Send: going OUT from this warehouse to another
            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])
            # To Accept: coming IN to this warehouse from another
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', own_locs.ids),
                ('location_id', 'in', other_locs.ids),
            ])

    def action_open_to_send(self):
        """Open outgoing cross-warehouse transfers for this picking type's warehouse."""
        self.ensure_one()
        all_wh_ids = self.env['stock.warehouse'].search([]).ids
        wh_id = self.warehouse_id.id

        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', wh_id),
            ('usage', '=', 'internal'),
        ])
        other_ids = [w for w in all_wh_ids if w != wh_id]
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', 'in', other_ids),
            ('usage', '=', 'internal'),
        ]) if other_ids else self.env['stock.location']

        return {
            'name': 'To Send',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'target': 'current',
            'domain': [
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ],
        }

    def action_open_to_accept(self):
        """Open incoming cross-warehouse transfers for this picking type's warehouse."""
        self.ensure_one()
        all_wh_ids = self.env['stock.warehouse'].search([]).ids
        wh_id = self.warehouse_id.id

        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', wh_id),
            ('usage', '=', 'internal'),
        ])
        other_ids = [w for w in all_wh_ids if w != wh_id]
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', 'in', other_ids),
            ('usage', '=', 'internal'),
        ]) if other_ids else self.env['stock.location']

        return {
            'name': 'To Accept',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'target': 'current',
            'domain': [
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', own_locs.ids),
                ('location_id', 'in', other_locs.ids),
            ],
        }


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    send_accept_label = fields.Char(
        string='Send/Accept',
        compute='_compute_send_accept_label',
        store=False,
    )

    @api.depends('location_id.warehouse_id', 'location_dest_id.warehouse_id', 'picking_type_code')
    def _compute_send_accept_label(self):
        for pick in self:
            if pick.picking_type_code != 'internal':
                pick.send_accept_label = False
                continue
            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id
            if src_wh and dst_wh and src_wh != dst_wh:
                pick.send_accept_label = 'To Send'
            else:
                pick.send_accept_label = False