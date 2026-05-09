# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# ──────────────────────────────────────────────────────────────────────────────
# Cross-WH Transfer flow:
#   1. Sender clicks [Send]   → wh_send_state: pending → sent
#                               Triggers check_availability; To Send count ↓
#   2. Receiver (or sender) clicks [Accept] → validates the transfer
#                               wh_send_state: sent → accepted; To Accept ↓
#
# wh_send_state values:
#   'na'       – not a cross-WH transfer (default)
#   'pending'  – cross-WH, not yet sent
#   'sent'     – sender clicked Send; awaiting acceptance
#   'accepted' – fully validated
# ──────────────────────────────────────────────────────────────────────────────

WH_SEND_STATE = [
    ('na',       'N/A'),
    ('pending',  'Pending'),
    ('sent',     'Sent'),
    ('accepted', 'Accepted'),
]


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

            other_locs = self.env['stock.location'].search([
                ('warehouse_id', '!=', pt.warehouse_id.id),
                ('warehouse_id', '!=', False),
                ('usage', '=', 'internal'),
            ])

            # To Send: cross-WH transfers originating HERE that are NOT yet sent
            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('wh_send_state', 'in', ['pending', 'na']),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])

            # To Accept: cross-WH transfers arriving HERE that have been sent
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned']),
                ('wh_send_state', '=', 'sent'),
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
        return self._build_action(_('To Send'), [
            ('state', 'in', ['confirmed', 'assigned']),
            ('wh_send_state', 'in', ['pending', 'na']),
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
        return self._build_action(_('To Accept'), [
            ('state', 'in', ['confirmed', 'assigned']),
            ('wh_send_state', '=', 'sent'),
            ('location_id', 'in', other_locs.ids),
            ('location_dest_id', 'in', own_locs.ids),
        ])


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ── Cross-WH send/accept workflow state ───────────────────────────────────
    wh_send_state = fields.Selection(
        WH_SEND_STATE,
        string='WH Transfer State',
        default='na',
        copy=False,
        index=True,
    )

    # ── Computed helpers for the view ─────────────────────────────────────────
    wh_is_cross_transfer = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_is_cross_send = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_is_cross_accept = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    send_accept_label = fields.Char(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_show_send_btn = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
        string='Show Send Button',
    )
    wh_show_accept_btn = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
        string='Show Accept Button',
    )

    @api.depends(
        'location_id', 'location_dest_id', 'picking_type_code',
        'wh_send_state', 'state',
    )
    def _compute_wh_cross_flags(self):
        for pick in self:
            is_internal = (pick.picking_type_code == 'internal')
            src_wh = pick.location_id.warehouse_id
            dst_wh = pick.location_dest_id.warehouse_id
            is_cross = bool(
                is_internal and src_wh and dst_wh and src_wh != dst_wh
            )
            not_done = pick.state not in ('done', 'cancel')

            pick.wh_is_cross_transfer = is_cross

            if is_cross:
                # Outgoing from src_wh perspective
                # (we show these fields regardless of which WH the user is in;
                #  the button visibility is handled by wh_send_state)
                pick.wh_is_cross_send = True
                pick.wh_is_cross_accept = True

                # Label for list view badge
                if pick.wh_send_state in ('pending', 'na'):
                    pick.send_accept_label = 'To Send'
                elif pick.wh_send_state == 'sent':
                    pick.send_accept_label = 'To Accept'
                else:
                    pick.send_accept_label = False

                # [Send] visible when: cross-WH, not yet sent, transfer active
                pick.wh_show_send_btn = (
                    not_done and pick.wh_send_state in ('pending', 'na')
                )
                # [Accept] visible when: cross-WH, already sent, transfer active
                # Both the receiver AND the sender can accept (validate)
                pick.wh_show_accept_btn = (
                    not_done and pick.wh_send_state == 'sent'
                )
            else:
                pick.wh_is_cross_send = False
                pick.wh_is_cross_accept = False
                pick.send_accept_label = False
                pick.wh_show_send_btn = False
                pick.wh_show_accept_btn = False

    # ── Send action ───────────────────────────────────────────────────────────
    def action_wh_send(self):
        """Mark this transfer as 'sent' so the destination WH can accept it."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('Cannot send a completed or cancelled transfer.'))
        if self.wh_send_state not in ('pending', 'na'):
            raise UserError(_('This transfer has already been sent.'))

        # Trigger availability check so quantities are reserved
        if self.state == 'confirmed':
            self.action_assign()

        self.wh_send_state = 'sent'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Sent'),
                'message': _(
                    'Transfer %s has been marked as sent. '
                    'The destination warehouse can now accept it.'
                ) % self.name,
                'type': 'success',
                'sticky': False,
            },
        }

    # ── Accept action ─────────────────────────────────────────────────────────
    def action_wh_accept(self):
        """Accept and validate this incoming cross-WH transfer."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('Cannot accept a completed or cancelled transfer.'))
        if self.wh_send_state != 'sent':
            raise UserError(_(
                'This transfer must be sent first before it can be accepted.'
            ))

        # If not all quantities are set, use immediate transfer (set qty = demand)
        for ml in self.move_line_ids:
            if not ml.quantity:
                ml.quantity = ml.reserved_uom_qty or ml.move_id.product_uom_qty

        # For moves without move_lines, set qty_done on the move itself
        for move in self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
            if not move.move_line_ids:
                move.quantity = move.product_uom_qty

        # Mark as accepted before validation
        self.wh_send_state = 'accepted'

        # Validate the transfer
        res = self.with_context(skip_backorder=True).button_validate()

        # If Odoo shows a backorder wizard, let it through
        if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            return res

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Accepted & Validated'),
                'message': _('Transfer %s has been validated successfully.') % self.name,
                'type': 'success',
                'sticky': False,
            },
        }
