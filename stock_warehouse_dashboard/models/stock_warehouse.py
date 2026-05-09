# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    to_send_count = fields.Integer(
        string='To Send',
        compute='_compute_to_send_count',
    )
    to_accept_count = fields.Integer(
        string='To Accept',
        compute='_compute_to_accept_count',
    )

    def _get_other_wh_locations(self, exclude_wh_id):
        all_wh_ids = self.search([]).ids
        other_ids = [w for w in all_wh_ids if w != exclude_wh_id]
        if not other_ids:
            return self.env['stock.location']
        return self.env['stock.location'].search([
            ('warehouse_id', 'in', other_ids),
            ('usage', '=', 'internal'),
        ])

    @api.depends_context('uid')
    def _compute_to_send_count(self):
        Picking = self.env['stock.picking']
        for wh in self:
            src_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            other_locs = self._get_other_wh_locations(wh.id)
            if not src_locs or not other_locs:
                wh.to_send_count = 0
                continue
            wh.to_send_count = Picking.search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', src_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])

    @api.depends_context('uid')
    def _compute_to_accept_count(self):
        Picking = self.env['stock.picking']
        for wh in self:
            dest_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            other_locs = self._get_other_wh_locations(wh.id)
            if not dest_locs or not other_locs:
                wh.to_accept_count = 0
                continue
            wh.to_accept_count = Picking.search_count([
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', dest_locs.ids),
                ('location_id', 'in', other_locs.ids),
            ])

    def action_open_to_send(self):
        self.ensure_one()
        src_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self._get_other_wh_locations(self.id)
        return {
            'name': 'To Send – %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', src_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ],
        }

    def action_open_to_accept(self):
        self.ensure_one()
        dest_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self._get_other_wh_locations(self.id)
        return {
            'name': 'To Accept – %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [
                ('picking_type_code', '=', 'internal'),
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_dest_id', 'in', dest_locs.ids),
                ('location_id', 'in', other_locs.ids),
            ],
        }


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    wh_to_send_count = fields.Integer(
        string='To Send',
        compute='_compute_wh_transfer_counts',
    )
    wh_to_accept_count = fields.Integer(
        string='To Accept',
        compute='_compute_wh_transfer_counts',
    )

    @api.depends('warehouse_id')
    def _compute_wh_transfer_counts(self):
        Picking = self.env['stock.picking']
        all_wh_ids = self.env['stock.warehouse'].search([]).ids

        for pt in self:
            wh = pt.warehouse_id
            if not wh:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            src_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            other_ids = [w for w in all_wh_ids if w != wh.id]
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
