# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    to_send_count = fields.Integer(compute='_compute_to_send_count')
    to_accept_count = fields.Integer(compute='_compute_to_accept_count')

    def _get_own_internal_locations(self):
        return self.env['stock.location'].search([
            ('warehouse_id', '=', self.id),
            ('usage', '=', 'internal'),
        ])

    def _get_other_internal_locations(self):
        all_wh_ids = self.search([]).ids
        other_ids = [w for w in all_wh_ids if w != self.id]
        if not other_ids:
            return self.env['stock.location']
        return self.env['stock.location'].search([
            ('warehouse_id', 'in', other_ids),
            ('usage', '=', 'internal'),
        ])

    @api.depends_context('uid')
    def _compute_to_send_count(self):
        for wh in self:
            src = wh._get_own_internal_locations()
            other = wh._get_other_internal_locations()
            wh.to_send_count = self.env['stock.picking'].search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', src.ids),
                ('location_dest_id', 'in', other.ids),
            ]) if src and other else 0

    @api.depends_context('uid')
    def _compute_to_accept_count(self):
        for wh in self:
            dest = wh._get_own_internal_locations()
            other = wh._get_other_internal_locations()
            wh.to_accept_count = self.env['stock.picking'].search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', dest.ids),
                ('location_id', 'in', other.ids),
            ]) if dest and other else 0

    def action_open_to_send(self):
        self.ensure_one()
        src = self._get_own_internal_locations()
        other = self._get_other_internal_locations()
        return {
            'name': 'To Send',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', src.ids),
                ('location_dest_id', 'in', other.ids),
            ],
        }

    def action_open_to_accept(self):
        self.ensure_one()
        dest = self._get_own_internal_locations()
        other = self._get_other_internal_locations()
        return {
            'name': 'To Accept',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', dest.ids),
                ('location_id', 'in', other.ids),
            ],
        }


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
    wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')

    @api.depends('code', 'warehouse_id')
    def _compute_wh_transfer_counts(self):
        Picking = self.env['stock.picking']
        all_wh_ids = self.env['stock.warehouse'].search([]).ids

        for pt in self:
            # ── Only Internal Transfer cards get badges ──────────────────────
            if pt.code != 'internal' or not pt.warehouse_id:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            wh_id = pt.warehouse_id.id
            src_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh_id),
                ('usage', '=', 'internal'),
            ])
            other_ids = [w for w in all_wh_ids if w != wh_id]
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', 'in', other_ids),
                ('usage', '=', 'internal'),
            ]) if other_ids else self.env['stock.location']

            if not src_locs or not other_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            pt.wh_to_send_count = Picking.search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', src_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])
            pt.wh_to_accept_count = Picking.search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', src_locs.ids),
                ('location_id', 'in', other_locs.ids),
            ])


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

            # Cross-warehouse transfer
            if src_wh and dst_wh and src_wh != dst_wh:
                pick.send_accept_label = 'To Send'   # from the source WH perspective
            else:
                pick.send_accept_label = False
