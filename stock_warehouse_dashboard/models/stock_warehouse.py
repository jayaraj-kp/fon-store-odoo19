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

    @api.depends_context('uid')
    def _compute_to_send_count(self):
        """
        Outgoing internal transfers from this warehouse to another warehouse
        that are Ready/Confirmed but not yet validated.
        """
        Picking = self.env['stock.picking']
        all_wh_ids = self.search([]).ids

        for wh in self:
            src_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', 'in', [w for w in all_wh_ids if w != wh.id]),
                ('usage', '=', 'internal'),
            ])
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
        """
        Incoming internal transfers arriving at this warehouse from another
        warehouse that are Ready/Confirmed but not yet validated.
        """
        Picking = self.env['stock.picking']
        all_wh_ids = self.search([]).ids

        for wh in self:
            dest_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', 'in', [w for w in all_wh_ids if w != wh.id]),
                ('usage', '=', 'internal'),
            ])
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
        all_wh_ids = self.search([]).ids
        src_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', 'in', [w for w in all_wh_ids if w != self.id]),
            ('usage', '=', 'internal'),
        ])
        return {
            'name': f'To Send – {self.name}',
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
        all_wh_ids = self.search([]).ids
        dest_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', 'in', [w for w in all_wh_ids if w != self.id]),
            ('usage', '=', 'internal'),
        ])
        return {
            'name': f'To Accept – {self.name}',
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
        """
        Delegate to the warehouse computed fields so that
        these values are available directly on picking type records
        (used in the kanban view).
        """
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
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', 'in', [w for w in all_wh_ids if w != wh.id]),
                ('usage', '=', 'internal'),
            ])

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
