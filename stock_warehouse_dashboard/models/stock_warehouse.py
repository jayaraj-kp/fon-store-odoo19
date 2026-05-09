# -*- coding: utf-8 -*-
from odoo import models, fields, api
# ──────────────────────────────────────────────────────────────────────────────
# NO transit location logic here.
# To Send  = outgoing internal transfers (src WH → other WH) ready/confirmed
# To Accept = incoming internal transfers (other WH → this WH) ready/confirmed
# Direct stock → stock, no transit hop.
# ──────────────────────────────────────────────────────────────────────────────


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    wh_to_send_count = fields.Integer(compute='_compute_wh_transfer_counts')
    wh_to_accept_count = fields.Integer(compute='_compute_wh_transfer_counts')

    @api.depends('code', 'warehouse_id')
    def _compute_wh_transfer_counts(self):
        Picking = self.env['stock.picking']
        for pt in self:
            if pt.code != 'internal' or not pt.warehouse_id:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            # All internal locations belonging to this warehouse
            own_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', pt.warehouse_id.id),
                ('usage', '=', 'internal'),
            ])
            if not own_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            # All internal locations NOT belonging to this warehouse
            other_locs = self.env['stock.location'].search([
                ('warehouse_id', '!=', pt.warehouse_id.id),
                ('warehouse_id', '!=', False),
                ('usage', '=', 'internal'),
            ])

            # To Send: transfers going OUT from this WH to another WH
            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])

            # To Accept: transfers coming IN to this WH from another WH
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', other_locs.ids),
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
        self.ensure_one()
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', '!=', self.warehouse_id.id),
            ('warehouse_id', '!=', False),
            ('usage', '=', 'internal'),
        ])
        return self._build_action('To Send', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', 'in', own_locs.ids),
            ('location_dest_id', 'in', other_locs.ids),
        ])

    def action_open_to_accept(self):
        self.ensure_one()
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('usage', '=', 'internal'),
        ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', '!=', self.warehouse_id.id),
            ('warehouse_id', '!=', False),
            ('usage', '=', 'internal'),
        ])
        return self._build_action('To Accept', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', 'in', other_locs.ids),
            ('location_dest_id', 'in', own_locs.ids),
        ])


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    send_accept_label = fields.Char(
        compute='_compute_wh_send_labels',
        store=False,
    )
    wh_is_cross_send = fields.Boolean(
        compute='_compute_wh_send_labels',
        store=False,
    )
    wh_is_cross_accept = fields.Boolean(
        compute='_compute_wh_send_labels',
        store=False,
    )

    @api.depends('location_id', 'location_dest_id', 'picking_type_code')
    def _compute_wh_send_labels(self):
        for pick in self:
            if pick.picking_type_code != 'internal':
                pick.send_accept_label = False
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = False
                continue

            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id

            # Cross-WH outgoing (To Send)
            if src_wh and dst_wh and src_wh != dst_wh:
                pick.send_accept_label = 'To Send'
                pick.wh_is_cross_send = True
                pick.wh_is_cross_accept = False

            # Cross-WH incoming (To Accept) — dest is this WH, src is another WH
            elif src_wh and dst_wh and src_wh != dst_wh:
                pick.send_accept_label = 'To Accept'
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = True

            else:
                pick.send_accept_label = False
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = False

    # ── NO action_confirm override ────────────────────────────────────────────
    # ── NO wh_transit_dest_wh_id field ───────────────────────────────────────
    # ── NO action_wh_send / action_wh_accept ─────────────────────────────────
    # ── NO _migrate_cross_wh_transfers ───────────────────────────────────────
    # All transit interception has been removed intentionally.
    # Cross-WH transfers go directly stock → stock as Odoo standard.