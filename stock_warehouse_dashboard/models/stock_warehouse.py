# # # # -*- coding: utf-8 -*-
# # # from odoo import models, fields, api
# # #
# # #
# # # class StockPickingType(models.Model):
# # #     _inherit = 'stock.picking.type'
# # #
# # #     wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
# # #     wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')
# # #
# # #     @api.depends('code', 'warehouse_id', 'default_location_src_id', 'default_location_dest_id')
# # #     def _compute_wh_transfer_counts(self):
# # #         Picking = self.env['stock.picking']
# # #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# # #
# # #         for pt in self:
# # #             # Only Internal Transfer cards get badges
# # #             if pt.code != 'internal' or not pt.warehouse_id:
# # #                 pt.wh_to_send_count = 0
# # #                 pt.wh_to_accept_count = 0
# # #                 continue
# # #
# # #             wh_id = pt.warehouse_id.id
# # #             # All internal locations belonging to THIS warehouse
# # #             own_locs = self.env['stock.location'].search([
# # #                 ('warehouse_id', '=', wh_id),
# # #                 ('usage', '=', 'internal'),
# # #             ])
# # #             # All internal locations belonging to OTHER warehouses
# # #             other_ids = [w for w in all_wh_ids if w != wh_id]
# # #             other_locs = self.env['stock.location'].search([
# # #                 ('warehouse_id', 'in', other_ids),
# # #                 ('usage', '=', 'internal'),
# # #             ]) if other_ids else self.env['stock.location']
# # #
# # #             if not own_locs or not other_locs:
# # #                 pt.wh_to_send_count = 0
# # #                 pt.wh_to_accept_count = 0
# # #                 continue
# # #
# # #             # To Send: going OUT from this warehouse to another
# # #             pt.wh_to_send_count = Picking.search_count([
# # #                 ('state', 'in', ['confirmed', 'assigned']),
# # #                 ('location_id', 'in', own_locs.ids),
# # #                 ('location_dest_id', 'in', other_locs.ids),
# # #             ])
# # #             # To Accept: coming IN to this warehouse from another
# # #             pt.wh_to_accept_count = Picking.search_count([
# # #                 ('state', 'in', ['confirmed', 'assigned']),
# # #                 ('location_dest_id', 'in', own_locs.ids),
# # #                 ('location_id', 'in', other_locs.ids),
# # #             ])
# # #
# # #     def action_open_to_send(self):
# # #         """Open outgoing cross-warehouse transfers for this picking type's warehouse."""
# # #         self.ensure_one()
# # #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# # #         wh_id = self.warehouse_id.id
# # #
# # #         own_locs = self.env['stock.location'].search([
# # #             ('warehouse_id', '=', wh_id),
# # #             ('usage', '=', 'internal'),
# # #         ])
# # #         other_ids = [w for w in all_wh_ids if w != wh_id]
# # #         other_locs = self.env['stock.location'].search([
# # #             ('warehouse_id', 'in', other_ids),
# # #             ('usage', '=', 'internal'),
# # #         ]) if other_ids else self.env['stock.location']
# # #
# # #         return {
# # #             'name': 'To Send',
# # #             'type': 'ir.actions.act_window',
# # #             'res_model': 'stock.picking',
# # #             'view_mode': 'list,form',
# # #             'domain': [
# # #                 ('state', 'in', ['confirmed', 'assigned']),
# # #                 ('location_id', 'in', own_locs.ids),
# # #                 ('location_dest_id', 'in', other_locs.ids),
# # #             ],
# # #         }
# # #
# # #     def action_open_to_accept(self):
# # #         """Open incoming cross-warehouse transfers for this picking type's warehouse."""
# # #         self.ensure_one()
# # #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# # #         wh_id = self.warehouse_id.id
# # #
# # #         own_locs = self.env['stock.location'].search([
# # #             ('warehouse_id', '=', wh_id),
# # #             ('usage', '=', 'internal'),
# # #         ])
# # #         other_ids = [w for w in all_wh_ids if w != wh_id]
# # #         other_locs = self.env['stock.location'].search([
# # #             ('warehouse_id', 'in', other_ids),
# # #             ('usage', '=', 'internal'),
# # #         ]) if other_ids else self.env['stock.location']
# # #
# # #         return {
# # #             'name': 'To Accept',
# # #             'type': 'ir.actions.act_window',
# # #             'res_model': 'stock.picking',
# # #             'view_mode': 'list,form',
# # #             'domain': [
# # #                 ('state', 'in', ['confirmed', 'assigned']),
# # #                 ('location_dest_id', 'in', own_locs.ids),
# # #                 ('location_id', 'in', other_locs.ids),
# # #             ],
# # #         }
# # #
# # #
# # # class StockPicking(models.Model):
# # #     _inherit = 'stock.picking'
# # #
# # #     send_accept_label = fields.Char(
# # #         string='Send/Accept',
# # #         compute='_compute_send_accept_label',
# # #         store=False,
# # #     )
# # #
# # #     @api.depends('location_id.warehouse_id', 'location_dest_id.warehouse_id', 'picking_type_code')
# # #     def _compute_send_accept_label(self):
# # #         for pick in self:
# # #             if pick.picking_type_code != 'internal':
# # #                 pick.send_accept_label = False
# # #                 continue
# # #             src_wh = pick.location_id.warehouse_id
# # #             dst_wh = pick.location_dest_id.warehouse_id
# # #             if src_wh and dst_wh and src_wh != dst_wh:
# # #                 pick.send_accept_label = 'To Send'
# # #             else:
# # #                 pick.send_accept_label = False
# # # -*- coding: utf-8 -*-
# # from odoo import models, fields, api
# #
# #
# # class StockPickingType(models.Model):
# #     _inherit = 'stock.picking.type'
# #
# #     wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
# #     wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')
# #
# #     @api.depends('code', 'warehouse_id', 'default_location_src_id', 'default_location_dest_id')
# #     def _compute_wh_transfer_counts(self):
# #         Picking = self.env['stock.picking']
# #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# #
# #         for pt in self:
# #             # Only Internal Transfer cards get badges
# #             if pt.code != 'internal' or not pt.warehouse_id:
# #                 pt.wh_to_send_count = 0
# #                 pt.wh_to_accept_count = 0
# #                 continue
# #
# #             wh_id = pt.warehouse_id.id
# #             # All internal locations belonging to THIS warehouse
# #             own_locs = self.env['stock.location'].search([
# #                 ('warehouse_id', '=', wh_id),
# #                 ('usage', '=', 'internal'),
# #             ])
# #             # All internal locations belonging to OTHER warehouses
# #             other_ids = [w for w in all_wh_ids if w != wh_id]
# #             other_locs = self.env['stock.location'].search([
# #                 ('warehouse_id', 'in', other_ids),
# #                 ('usage', '=', 'internal'),
# #             ]) if other_ids else self.env['stock.location']
# #
# #             if not own_locs or not other_locs:
# #                 pt.wh_to_send_count = 0
# #                 pt.wh_to_accept_count = 0
# #                 continue
# #
# #             # To Send: going OUT from this warehouse to another
# #             pt.wh_to_send_count = Picking.search_count([
# #                 ('state', 'in', ['confirmed', 'assigned']),
# #                 ('location_id', 'in', own_locs.ids),
# #                 ('location_dest_id', 'in', other_locs.ids),
# #             ])
# #             # To Accept: coming IN to this warehouse from another
# #             pt.wh_to_accept_count = Picking.search_count([
# #                 ('state', 'in', ['confirmed', 'assigned']),
# #                 ('location_dest_id', 'in', own_locs.ids),
# #                 ('location_id', 'in', other_locs.ids),
# #             ])
# #
# #     def action_open_to_send(self):
# #         """Open outgoing cross-warehouse transfers for this picking type's warehouse."""
# #         self.ensure_one()
# #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# #         wh_id = self.warehouse_id.id
# #
# #         own_locs = self.env['stock.location'].search([
# #             ('warehouse_id', '=', wh_id),
# #             ('usage', '=', 'internal'),
# #         ])
# #         other_ids = [w for w in all_wh_ids if w != wh_id]
# #         other_locs = self.env['stock.location'].search([
# #             ('warehouse_id', 'in', other_ids),
# #             ('usage', '=', 'internal'),
# #         ]) if other_ids else self.env['stock.location']
# #
# #         return {
# #             'name': 'To Send',
# #             'type': 'ir.actions.act_window',
# #             'res_model': 'stock.picking',
# #             'view_mode': 'list,form',
# #             'views': [(False, 'list'), (False, 'form')],
# #             'target': 'current',
# #             'domain': [
# #                 ('state', 'in', ['confirmed', 'assigned']),
# #                 ('location_id', 'in', own_locs.ids),
# #                 ('location_dest_id', 'in', other_locs.ids),
# #             ],
# #         }
# #
# #     def action_open_to_accept(self):
# #         """Open incoming cross-warehouse transfers for this picking type's warehouse."""
# #         self.ensure_one()
# #         all_wh_ids = self.env['stock.warehouse'].search([]).ids
# #         wh_id = self.warehouse_id.id
# #
# #         own_locs = self.env['stock.location'].search([
# #             ('warehouse_id', '=', wh_id),
# #             ('usage', '=', 'internal'),
# #         ])
# #         other_ids = [w for w in all_wh_ids if w != wh_id]
# #         other_locs = self.env['stock.location'].search([
# #             ('warehouse_id', 'in', other_ids),
# #             ('usage', '=', 'internal'),
# #         ]) if other_ids else self.env['stock.location']
# #
# #         return {
# #             'name': 'To Accept',
# #             'type': 'ir.actions.act_window',
# #             'res_model': 'stock.picking',
# #             'view_mode': 'list,form',
# #             'views': [(False, 'list'), (False, 'form')],
# #             'target': 'current',
# #             'domain': [
# #                 ('state', 'in', ['confirmed', 'assigned']),
# #                 ('location_dest_id', 'in', own_locs.ids),
# #                 ('location_id', 'in', other_locs.ids),
# #             ],
# #         }
# #
# #
# # class StockPicking(models.Model):
# #     _inherit = 'stock.picking'
# #
# #     send_accept_label = fields.Char(
# #         string='Send/Accept',
# #         compute='_compute_send_accept_label',
# #         store=False,
# #     )
# #
# #     @api.depends('location_id.warehouse_id', 'location_dest_id.warehouse_id', 'picking_type_code')
# #     def _compute_send_accept_label(self):
# #         for pick in self:
# #             if pick.picking_type_code != 'internal':
# #                 pick.send_accept_label = False
# #                 continue
# #             src_wh = pick.location_id.warehouse_id
# #             dst_wh = pick.location_dest_id.warehouse_id
# #             if src_wh and dst_wh and src_wh != dst_wh:
# #                 pick.send_accept_label = 'To Send'
# #             else:
# #                 pick.send_accept_label = False
#
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
#             if pt.code != 'internal' or not pt.warehouse_id:
#                 pt.wh_to_send_count = 0
#                 pt.wh_to_accept_count = 0
#                 continue
#
#             wh_id = pt.warehouse_id.id
#             own_locs = self.env['stock.location'].search([
#                 ('warehouse_id', '=', wh_id), ('usage', '=', 'internal'),
#             ])
#             other_ids = [w for w in all_wh_ids if w != wh_id]
#             other_locs = self.env['stock.location'].search([
#                 ('warehouse_id', 'in', other_ids), ('usage', '=', 'internal'),
#             ]) if other_ids else self.env['stock.location']
#
#             if not own_locs or not other_locs:
#                 pt.wh_to_send_count = 0
#                 pt.wh_to_accept_count = 0
#                 continue
#
#             pt.wh_to_send_count = Picking.search_count([
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_id', 'in', own_locs.ids),
#                 ('location_dest_id', 'in', other_locs.ids),
#             ])
#             pt.wh_to_accept_count = Picking.search_count([
#                 ('state', 'in', ['confirmed', 'assigned']),
#                 ('location_dest_id', 'in', own_locs.ids),
#                 ('location_id', 'in', other_locs.ids),
#             ])
#
#     def _build_action(self, name, domain):
#         return {
#             'name': name,
#             'type': 'ir.actions.act_window',
#             'res_model': 'stock.picking',
#             'view_mode': 'list,form',
#             'views': [(False, 'list'), (False, 'form')],
#             'target': 'current',
#             'domain': domain,
#         }
#
#     def action_open_to_send(self):
#         self.ensure_one()
#         all_wh_ids = self.env['stock.warehouse'].search([]).ids
#         wh_id = self.warehouse_id.id
#         own_locs = self.env['stock.location'].search([
#             ('warehouse_id', '=', wh_id), ('usage', '=', 'internal'),
#         ])
#         other_ids = [w for w in all_wh_ids if w != wh_id]
#         other_locs = self.env['stock.location'].search([
#             ('warehouse_id', 'in', other_ids), ('usage', '=', 'internal'),
#         ]) if other_ids else self.env['stock.location']
#         return self._build_action('To Send', [
#             ('state', 'in', ['confirmed', 'assigned']),
#             ('location_id', 'in', own_locs.ids),
#             ('location_dest_id', 'in', other_locs.ids),
#         ])
#
#     def action_open_to_accept(self):
#         self.ensure_one()
#         all_wh_ids = self.env['stock.warehouse'].search([]).ids
#         wh_id = self.warehouse_id.id
#         own_locs = self.env['stock.location'].search([
#             ('warehouse_id', '=', wh_id), ('usage', '=', 'internal'),
#         ])
#         other_ids = [w for w in all_wh_ids if w != wh_id]
#         other_locs = self.env['stock.location'].search([
#             ('warehouse_id', 'in', other_ids), ('usage', '=', 'internal'),
#         ]) if other_ids else self.env['stock.location']
#         return self._build_action('To Accept', [
#             ('state', 'in', ['confirmed', 'assigned']),
#             ('location_dest_id', 'in', own_locs.ids),
#             ('location_id', 'in', other_locs.ids),
#         ])
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
#     # True  = source location belongs to a different warehouse than dest → "Send"
#     # False = dest location belongs to a different warehouse than source → "Accept"
#     # None  = same warehouse or not internal → hide both custom buttons
#     wh_is_cross_send = fields.Boolean(
#         string='Is Cross-WH Send',
#         compute='_compute_wh_cross_type',
#         store=False,
#     )
#     wh_is_cross_accept = fields.Boolean(
#         string='Is Cross-WH Accept',
#         compute='_compute_wh_cross_type',
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
#
#     @api.depends('location_id.warehouse_id', 'location_dest_id.warehouse_id',
#                  'picking_type_code', 'picking_type_id.warehouse_id')
#     def _compute_wh_cross_type(self):
#         """
#         Determine if this picking is a cross-warehouse Send or Accept
#         from the perspective of the picking_type's warehouse.
#
#         - wh_is_cross_send  = True  → the picking type's WH is the SOURCE
#                                        (goods going OUT) → show "Send" button
#         - wh_is_cross_accept = True → the picking type's WH is the DEST
#                                        (goods coming IN) → show "Accept" button
#         """
#         for pick in self:
#             if pick.picking_type_code != 'internal':
#                 pick.wh_is_cross_send = False
#                 pick.wh_is_cross_accept = False
#                 continue
#
#             src_wh = pick.location_id.warehouse_id
#             dst_wh = pick.location_dest_id.warehouse_id
#
#             # Must be cross-warehouse
#             if not src_wh or not dst_wh or src_wh == dst_wh:
#                 pick.wh_is_cross_send = False
#                 pick.wh_is_cross_accept = False
#                 continue
#
#             # The picking_type's warehouse tells us which side we're on
#             pt_wh = pick.picking_type_id.warehouse_id
#             if pt_wh == src_wh:
#                 # Picking type belongs to the SOURCE warehouse → Send
#                 pick.wh_is_cross_send = True
#                 pick.wh_is_cross_accept = False
#             elif pt_wh == dst_wh:
#                 # Picking type belongs to the DEST warehouse → Accept
#                 pick.wh_is_cross_send = False
#                 pick.wh_is_cross_accept = True
#             else:
#                 pick.wh_is_cross_send = False
#                 pick.wh_is_cross_accept = False
#
#     def action_wh_send(self):
#         """'Send' button — validates the outgoing cross-warehouse transfer."""
#         return self.button_validate()
#
#     def action_wh_accept(self):
#         """'Accept' button — validates the incoming cross-warehouse transfer."""
#         return self.button_validate()
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


TRANSIT_LOCATION_ID = 10   # Inter-warehouse transit (id=10 confirmed from DB)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
    wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')

    @api.depends('code', 'warehouse_id', 'default_location_src_id', 'default_location_dest_id')
    def _compute_wh_transfer_counts(self):
        Picking = self.env['stock.picking']
        transit_id = TRANSIT_LOCATION_ID

        for pt in self:
            if pt.code != 'internal' or not pt.warehouse_id:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            wh_id = pt.warehouse_id.id
            own_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh_id),
                ('usage', '=', 'internal'),
            ])

            if not own_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            # To Send: leg-1 pickings — own stock → transit, with dest WH set
            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', '=', transit_id),
                ('wh_transit_dest_wh_id', '!=', False),
            ])

            # To Accept: leg-2 pickings — transit → own stock
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', '=', transit_id),
                ('location_dest_id', 'in', own_locs.ids),
            ])

    def _build_action(self, name, domain):
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'target': 'current',
            'domain': domain,
        }

    def action_open_to_send(self):
        """Open leg-1 pickings: own stock → transit."""
        self.ensure_one()
        transit_id = TRANSIT_LOCATION_ID
        wh_id = self.warehouse_id.id
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', wh_id),
            ('usage', '=', 'internal'),
        ])
        return self._build_action('To Send', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', 'in', own_locs.ids),
            ('location_dest_id', '=', transit_id),
            ('wh_transit_dest_wh_id', '!=', False),
        ])

    def action_open_to_accept(self):
        """Open leg-2 pickings: transit → own stock."""
        self.ensure_one()
        transit_id = TRANSIT_LOCATION_ID
        wh_id = self.warehouse_id.id
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', wh_id),
            ('usage', '=', 'internal'),
        ])
        return self._build_action('To Accept', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', '=', transit_id),
            ('location_dest_id', 'in', own_locs.ids),
        ])


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Stored on leg-1: which warehouse is the final destination
    wh_transit_dest_wh_id = fields.Many2one(
        'stock.warehouse',
        string='Transit Destination Warehouse',
        copy=False,
        help='Leg-1 cross-WH pickings only (stock → transit). '
             'Used to create leg-2 on Send.',
    )

    send_accept_label = fields.Char(
        string='Send/Accept',
        compute='_compute_send_accept_label',
        store=False,
    )

    wh_is_cross_send = fields.Boolean(
        compute='_compute_wh_cross_type',
        store=False,
    )
    wh_is_cross_accept = fields.Boolean(
        compute='_compute_wh_cross_type',
        store=False,
    )

    @api.depends('location_id', 'location_dest_id', 'picking_type_code',
                 'wh_transit_dest_wh_id')
    def _compute_send_accept_label(self):
        transit_id = TRANSIT_LOCATION_ID
        for pick in self:
            if pick.picking_type_code != 'internal':
                pick.send_accept_label = False
                continue
            if pick.location_dest_id.id == transit_id and pick.wh_transit_dest_wh_id:
                pick.send_accept_label = 'To Send'
            elif pick.location_id.id == transit_id:
                pick.send_accept_label = 'To Accept'
            else:
                pick.send_accept_label = False

    @api.depends('location_id', 'location_dest_id', 'picking_type_code',
                 'wh_transit_dest_wh_id')
    def _compute_wh_cross_type(self):
        transit_id = TRANSIT_LOCATION_ID
        for pick in self:
            if pick.picking_type_code != 'internal':
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = False
                continue
            # Leg 1: src/Stock → transit  → Send button
            if pick.location_dest_id.id == transit_id and pick.wh_transit_dest_wh_id:
                pick.wh_is_cross_send = True
                pick.wh_is_cross_accept = False
            # Leg 2: transit → dst/Stock  → Accept button
            elif pick.location_id.id == transit_id:
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = True
            else:
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = False

    # ------------------------------------------------------------------ #
    #  SEND: validate leg-1, auto-create leg-2 in destination WH          #
    # ------------------------------------------------------------------ #
    def action_wh_send(self):
        self.ensure_one()
        transit_loc = self.env['stock.location'].browse(TRANSIT_LOCATION_ID)
        dest_wh = self.wh_transit_dest_wh_id
        if not dest_wh:
            raise UserError(_('No destination warehouse set on this transfer.'))

        # Find destination WH Internal Transfers picking type
        dest_pt = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('code', '=', 'internal'),
            ('sequence_code', 'like', 'INT'),
        ], limit=1)
        if not dest_pt:
            dest_pt = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', dest_wh.id),
                ('code', '=', 'internal'),
            ], limit=1)

        # Find destination WH main Stock location
        dest_stock = self.env['stock.location'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('usage', '=', 'internal'),
            ('name', 'ilike', 'Stock'),
        ], limit=1)
        if not dest_stock:
            dest_stock = self.env['stock.location'].search([
                ('warehouse_id', '=', dest_wh.id),
                ('usage', '=', 'internal'),
            ], limit=1)

        # Snapshot quantities before validate (move_ids may change)
        move_data = [(
            m.product_id.id,
            m.product_uom.id,
            m.quantity,
            m.name,
        ) for m in self.move_ids if m.state not in ('done', 'cancel')]

        # Validate leg-1 (src/Stock → transit)
        result = self.button_validate()

        # Create leg-2: transit → dest/Stock
        move_vals = [(0, 0, {
            'name': name,
            'product_id': product_id,
            'product_uom': product_uom,
            'product_uom_qty': qty,
            'location_id': transit_loc.id,
            'location_dest_id': dest_stock.id,
            'origin': self.name,
        }) for product_id, product_uom, qty, name in move_data]

        leg2 = self.env['stock.picking'].create({
            'picking_type_id': dest_pt.id,
            'location_id': transit_loc.id,
            'location_dest_id': dest_stock.id,
            'origin': self.name,
            'move_ids': move_vals,
        })
        leg2.action_confirm()
        leg2.action_assign()

        return result

    # ------------------------------------------------------------------ #
    #  ACCEPT: validate leg-2 (transit → dst/Stock)                       #
    # ------------------------------------------------------------------ #
    def action_wh_accept(self):
        return self.button_validate()

    # ------------------------------------------------------------------ #
    #  Override action_confirm: intercept cross-WH internals,             #
    #  reroute destination to transit, store final dest WH                #
    # ------------------------------------------------------------------ #
    def action_confirm(self):
        res = super().action_confirm()
        transit_loc = self.env['stock.location'].browse(TRANSIT_LOCATION_ID)

        for pick in self:
            if pick.picking_type_code != 'internal':
                continue
            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id
            # Must be cross-warehouse and not already a transit leg
            if (not src_wh or not dst_wh or src_wh == dst_wh
                    or pick.location_dest_id.id == TRANSIT_LOCATION_ID
                    or pick.location_id.id == TRANSIT_LOCATION_ID):
                continue

            # Reroute leg-1: change dest to transit, remember final dest WH
            pick.write({
                'location_dest_id': transit_loc.id,
                'wh_transit_dest_wh_id': dst_wh.id,
            })
            for move in pick.move_ids:
                move.write({'location_dest_id': transit_loc.id})
                for ml in move.move_line_ids:
                    ml.write({'location_dest_id': transit_loc.id})

        return res