# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

TRANSIT_LOCATION_ID = 10  # Inter-warehouse transit (confirmed from DB)


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

            own_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', pt.warehouse_id.id),
                ('usage', '=', 'internal'),
            ])
            if not own_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', '=', TRANSIT_LOCATION_ID),
                ('wh_transit_dest_wh_id', '!=', False),
            ])
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('location_id', '=', TRANSIT_LOCATION_ID),
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
        return self._build_action('To Send', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', 'in', own_locs.ids),
            ('location_dest_id', '=', TRANSIT_LOCATION_ID),
            ('wh_transit_dest_wh_id', '!=', False),
        ])

    def action_open_to_accept(self):
        self.ensure_one()
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('usage', '=', 'internal'),
        ])
        return self._build_action('To Accept', [
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_id', '=', TRANSIT_LOCATION_ID),
            ('location_dest_id', 'in', own_locs.ids),
        ])


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    wh_transit_dest_wh_id = fields.Many2one(
        'stock.warehouse',
        string='Transit Destination Warehouse',
        copy=False,
        index=True,
    )

    send_accept_label = fields.Char(compute='_compute_wh_send_labels', store=False)
    wh_is_cross_send = fields.Boolean(compute='_compute_wh_send_labels', store=False)
    wh_is_cross_accept = fields.Boolean(compute='_compute_wh_send_labels', store=False)

    @api.depends('location_id', 'location_dest_id',
                 'picking_type_code', 'wh_transit_dest_wh_id')
    def _compute_wh_send_labels(self):
        for pick in self:
            is_internal = pick.picking_type_code == 'internal'
            is_leg1 = (pick.location_dest_id.id == TRANSIT_LOCATION_ID
                       and bool(pick.wh_transit_dest_wh_id))
            is_leg2 = (pick.location_id.id == TRANSIT_LOCATION_ID
                       and not pick.wh_transit_dest_wh_id)

            if is_internal and is_leg1:
                pick.send_accept_label  = 'To Send'
                pick.wh_is_cross_send   = True
                pick.wh_is_cross_accept = False
            elif is_internal and is_leg2:
                pick.send_accept_label  = 'To Accept'
                pick.wh_is_cross_send   = False
                pick.wh_is_cross_accept = True
            else:
                pick.send_accept_label  = False
                pick.wh_is_cross_send   = False
                pick.wh_is_cross_accept = False

    # ------------------------------------------------------------------
    #  SEND: validate leg-1, auto-create leg-2
    # ------------------------------------------------------------------
    def action_wh_send(self):
        self.ensure_one()
        dest_wh = self.wh_transit_dest_wh_id
        if not dest_wh:
            raise UserError(_('No destination warehouse found on this transfer.'))

        transit_loc = self.env['stock.location'].browse(TRANSIT_LOCATION_ID)

        dest_pt = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('code', '=', 'internal'),
            ('sequence_code', 'like', 'INT'),
        ], limit=1) or self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('code', '=', 'internal'),
        ], limit=1)

        dest_stock = self.env['stock.location'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('usage', '=', 'internal'),
            ('name', '=ilike', 'stock'),
        ], limit=1) or self.env['stock.location'].search([
            ('warehouse_id', '=', dest_wh.id),
            ('usage', '=', 'internal'),
        ], limit=1)

        if not dest_pt or not dest_stock:
            raise UserError(_(
                'Could not find Internal Transfers picking type or Stock '
                'location for warehouse %s.'
            ) % dest_wh.name)

        # Capture move data BEFORE validating
        move_data = [{
            'name': m.name,
            'product_id': m.product_id.id,
            'product_uom': m.product_uom.id,
            'product_uom_qty': m.quantity or m.product_uom_qty,
            'origin': self.name,
        } for m in self.move_ids.filtered(
            lambda mv: mv.state not in ('done', 'cancel'))]

        # Validate leg-1
        result = self.button_validate()

        # Create leg-2: transit → dest/Stock
        if move_data:
            leg2 = self.env['stock.picking'].create({
                'picking_type_id': dest_pt.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_stock.id,
                'origin': self.name,
                'move_ids': [(0, 0, dict(
                    m,
                    location_id=transit_loc.id,
                    location_dest_id=dest_stock.id,
                )) for m in move_data],
            })
            leg2.action_confirm()
            leg2.action_assign()

        return result

    # ------------------------------------------------------------------
    #  ACCEPT: validate leg-2
    # ------------------------------------------------------------------
    def action_wh_accept(self):
        return self.button_validate()

    # ------------------------------------------------------------------
    #  Intercept confirm: reroute cross-WH internals through transit
    # ------------------------------------------------------------------
    def action_confirm(self):
        res = super().action_confirm()
        transit_loc = self.env['stock.location'].browse(TRANSIT_LOCATION_ID)
        for pick in self:
            if pick.picking_type_code != 'internal':
                continue
            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id
            if (not src_wh or not dst_wh or src_wh == dst_wh
                    or pick.location_dest_id.id == TRANSIT_LOCATION_ID
                    or pick.location_id.id == TRANSIT_LOCATION_ID):
                continue
            pick.write({
                'location_dest_id': transit_loc.id,
                'wh_transit_dest_wh_id': dst_wh.id,
            })
            for move in pick.move_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel')):
                move.location_dest_id = transit_loc.id
                for ml in move.move_line_ids:
                    ml.location_dest_id = transit_loc.id
        return res

    # ------------------------------------------------------------------
    #  Auto-migrate existing cross-WH transfers on module install/upgrade
    #  Called from __manifest__.py post_init_hook and post_migrate_hook
    # ------------------------------------------------------------------
    @api.model
    def _migrate_cross_wh_transfers(self):
        """
        Finds any existing confirmed/assigned cross-WH internal transfers
        that go directly stock→stock (not via transit) and reroutes them
        through the Inter-warehouse transit location automatically.
        No manual SQL needed.
        """
        transit_loc = self.env['stock.location'].browse(TRANSIT_LOCATION_ID)
        if not transit_loc.exists():
            return

        all_wh = self.env['stock.warehouse'].search([])
        all_wh_loc_map = {}  # wh_id → location ids
        for wh in all_wh:
            locs = self.env['stock.location'].search([
                ('warehouse_id', '=', wh.id),
                ('usage', '=', 'internal'),
            ])
            all_wh_loc_map[wh.id] = locs.ids

        # Find all internal pickings in open states, not already transit legs
        candidates = self.search([
            ('picking_type_code', '=', 'internal'),
            ('state', 'in', ['confirmed', 'assigned']),
            ('location_dest_id', '!=', TRANSIT_LOCATION_ID),
            ('location_id', '!=', TRANSIT_LOCATION_ID),
            ('wh_transit_dest_wh_id', '=', False),
        ])

        for pick in candidates:
            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id
            if not src_wh or not dst_wh or src_wh == dst_wh:
                continue
            # Cross-WH transfer found — reroute to transit
            pick.write({
                'location_dest_id': transit_loc.id,
                'wh_transit_dest_wh_id': dst_wh.id,
            })
            for move in pick.move_ids.filtered(
                    lambda m: m.state not in ('done', 'cancel')):
                move.location_dest_id = transit_loc.id
                for ml in move.move_line_ids:
                    ml.location_dest_id = transit_loc.id