# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

# ──────────────────────────────────────────────────────────────────────────────
# Cross-WH Transfer flow:
#   1. Transfer is created → wh_send_state auto-set to 'pending'
#   2. Sender clicks [Send]   → wh_send_state: pending → sent
#                               Triggers check_availability; To Send count ↓
#   3. Receiver (or sender) clicks [Accept] → validates the transfer
#                               wh_send_state: sent → accepted; To Accept ↓
#                               *** Journal entry created (Accept only):
#                                   Dr Stock Transfer In  (receiver WH analytic)
#                                   Cr Stock Transfer Out (sender WH analytic) ***
#
# wh_send_state values:
#   'na'       – not a cross-WH transfer (default for non-cross-WH)
#   'pending'  – cross-WH, not yet sent by sender
#   'sent'     – sender clicked Send; destination WH can now Accept
#   'accepted' – fully validated
#
# For cross-WH transfers:
#   - Standard [Validate] button is hidden → users MUST use Send/Accept flow
#   - [Send] shown only when state == 'pending'
#   - [Accept] shown only when state == 'sent'
#
# AUTO-REPLENISHMENT SUPPORT:
#   Odoo replenishment rules create pickings in multiple steps and may use
#   transit locations that have no warehouse_id set directly on the location.
#   We resolve the warehouse by walking up the location parent tree.
#   We also override write() so that pickings whose locations are filled in
#   after creation (common with procurement rules) still get detected.
# ──────────────────────────────────────────────────────────────────────────────

WH_SEND_STATE = [
    ('na',       'N/A'),
    ('pending',  'Pending'),
    ('sent',     'Sent'),
    ('accepted', 'Accepted'),
]


def _resolve_warehouse(location):
    """
    Walk up the location parent chain until we find a warehouse_id.
    This handles transit locations that are children of a WH's view location
    but do not have warehouse_id set on themselves directly.
    Returns a warehouse record or an empty recordset.
    """
    loc = location
    while loc:
        if loc.warehouse_id:
            return loc.warehouse_id
        loc = loc.location_id  # parent
    return location.env['stock.warehouse'].browse()


# ──────────────────────────────────────────────────────────────────────────────
# Warehouse — accounting configuration fields
# ──────────────────────────────────────────────────────────────────────────────

class StockWarehouseAccounting(models.Model):
    """Extend stock.warehouse with accounting configuration for the
    cross-WH Accept journal entry."""
    _inherit = 'stock.warehouse'

    wh_stock_transfer_in_account_id = fields.Many2one(
        'account.account',
        string='Stock Transfer In Account',
        help='Debited on the Accept journal entry when this warehouse receives stock.',
    )
    wh_stock_transfer_out_account_id = fields.Many2one(
        'account.account',
        string='Stock Transfer Out Account',
        help='Credited on the Accept journal entry when this warehouse sends stock.',
    )

    wh_stock_journal_id = fields.Many2one(
        'account.journal',
        string='Stock Transfer Journal',
        domain=[('type', 'in', ['general', 'purchase', 'sale'])],
        help='Journal used for the Accept journal entry. '
             'Leave empty to auto-select the first "General" journal.',
    )

    wh_analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Warehouse analytic: debited when this warehouse receives stock, '
             'credited when this warehouse sends stock.',
    )


# ──────────────────────────────────────────────────────────────────────────────
# StockPickingType — dashboard counters
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

            # All internal locations that belong to this warehouse
            # (including children via parent_path — catches transit locs)
            own_wh_locs = self.env['stock.location'].search([
                ('complete_name', 'like', pt.warehouse_id.lot_stock_id.complete_name.split('/')[0]),
            ]) if pt.warehouse_id.lot_stock_id else self.env['stock.location']

            # Broader: any location whose resolved warehouse == this WH
            own_locs = self.env['stock.location'].search([
                ('warehouse_id', '=', pt.warehouse_id.id),
            ])
            # Also grab locations under this WH's parent view location
            if pt.warehouse_id.view_location_id:
                own_locs |= self.env['stock.location'].search([
                    ('id', 'child_of', pt.warehouse_id.view_location_id.id),
                ])

            if not own_locs:
                pt.wh_to_send_count = 0
                pt.wh_to_accept_count = 0
                continue

            other_locs = self.env['stock.location'].search([
                ('warehouse_id', '!=', pt.warehouse_id.id),
                ('warehouse_id', '!=', False),
            ])

            # To Send: cross-WH transfers FROM this WH not yet sent
            pt.wh_to_send_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned', 'waiting']),
                ('wh_send_state', '=', 'pending'),
                ('location_id', 'in', own_locs.ids),
                ('location_dest_id', 'in', other_locs.ids),
            ])

            # To Accept: cross-WH transfers arriving HERE that have been sent
            pt.wh_to_accept_count = Picking.search_count([
                ('state', 'in', ['confirmed', 'assigned', 'waiting']),
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
        ])
        if self.warehouse_id.view_location_id:
            own_locs |= self.env['stock.location'].search([
                ('id', 'child_of', self.warehouse_id.view_location_id.id),
            ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', '!=', self.warehouse_id.id),
            ('warehouse_id', '!=', False),
        ])
        return self._build_action(_('To Send'), [
            ('state', 'in', ['confirmed', 'assigned', 'waiting']),
            ('wh_send_state', '=', 'pending'),
            ('location_id', 'in', own_locs.ids),
            ('location_dest_id', 'in', other_locs.ids),
        ])

    def action_open_to_accept(self):
        self.ensure_one()
        own_locs = self.env['stock.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
        ])
        if self.warehouse_id.view_location_id:
            own_locs |= self.env['stock.location'].search([
                ('id', 'child_of', self.warehouse_id.view_location_id.id),
            ])
        other_locs = self.env['stock.location'].search([
            ('warehouse_id', '!=', self.warehouse_id.id),
            ('warehouse_id', '!=', False),
        ])
        return self._build_action(_('To Accept'), [
            ('state', 'in', ['confirmed', 'assigned', 'waiting']),
            ('wh_send_state', '=', 'sent'),
            ('location_id', 'in', other_locs.ids),
            ('location_dest_id', 'in', own_locs.ids),
        ])


# ──────────────────────────────────────────────────────────────────────────────
# StockPicking — cross-WH workflow + journal entries
# ──────────────────────────────────────────────────────────────────────────────

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ── Stored workflow state for cross-WH transfers ──────────────────────────
    wh_send_state = fields.Selection(
        WH_SEND_STATE,
        string='WH Transfer State',
        default='na',
        copy=False,
        index=True,
    )

    wh_accept_journal_entry_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        copy=False,
        readonly=True,
        help='Journal entry automatically created when [Accept] is clicked.',
    )

    # ── Computed display flags (not stored — always fresh) ────────────────────
    wh_is_cross_transfer = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_show_send_btn = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_show_accept_btn = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
    )
    wh_hide_validate_btn = fields.Boolean(
        compute='_compute_wh_cross_flags',
        store=False,
        string='Hide standard Validate button',
    )
    send_accept_label = fields.Char(
        compute='_compute_wh_cross_flags',
        store=False,
    )

    @api.depends(
        'location_id', 'location_dest_id', 'picking_type_id',
        'wh_send_state', 'state',
    )
    def _compute_wh_cross_flags(self):
        for pick in self:
            src_wh = _resolve_warehouse(pick.location_id)
            dst_wh = _resolve_warehouse(pick.location_dest_id)
            is_internal = (pick.picking_type_id.code == 'internal')
            is_cross = bool(
                is_internal and src_wh and dst_wh and src_wh != dst_wh
            )
            not_done = pick.state not in ('done', 'cancel')

            pick.wh_is_cross_transfer = is_cross

            if is_cross and not_done:
                pick.wh_show_send_btn = (pick.wh_send_state == 'pending')
                pick.wh_show_accept_btn = (pick.wh_send_state == 'sent')
                pick.wh_hide_validate_btn = True
                if pick.wh_send_state == 'pending':
                    pick.send_accept_label = 'To Send'
                elif pick.wh_send_state == 'sent':
                    pick.send_accept_label = 'To Accept'
                else:
                    pick.send_accept_label = False
            else:
                pick.wh_show_send_btn = False
                pick.wh_show_accept_btn = False
                pick.wh_hide_validate_btn = False
                pick.send_accept_label = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _wh_is_cross_wh_internal(self):
        """
        Return True if this picking is an internal transfer between two
        different warehouses. Uses _resolve_warehouse() to handle transit
        locations that have no warehouse_id set directly.
        """
        self.ensure_one()
        if self.picking_type_id.code != 'internal':
            return False
        src_wh = _resolve_warehouse(self.location_id)
        dst_wh = _resolve_warehouse(self.location_dest_id)
        return bool(src_wh and dst_wh and src_wh != dst_wh)

    def _wh_try_set_pending(self):
        """
        Set wh_send_state = 'pending' on self if it qualifies as a
        cross-WH internal transfer and is still in 'na' state.
        Safe to call multiple times (idempotent).
        """
        for pick in self:
            if pick.wh_send_state == 'na' and pick._wh_is_cross_wh_internal():
                # Use sudo to avoid any access-right issues during auto-creation
                pick.sudo().wh_send_state = 'pending'

    def _invalidate_picking_type_counts(self):
        """
        Tell Odoo to recompute wh_to_send_count / wh_to_accept_count on
        any related picking types so dashboard badges refresh immediately.
        """
        pt_ids = self.mapped('picking_type_id')
        if pt_ids:
            pt_ids.invalidate_recordset(['wh_to_send_count', 'wh_to_accept_count'])

    def _wh_get_journal(self, warehouse):
        """
        Return the journal to use for warehouse transfer entries.
        Falls back to the first 'general' journal in the company if not set.
        """
        if warehouse.wh_stock_journal_id:
            return warehouse.wh_stock_journal_id
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', (warehouse.company_id or self.env.company).id),
        ], limit=1)
        return journal

    def _wh_compute_accept_amount(self):
        """
        Compute total monetary value for the Accept journal entry.
        Prefers Stock Valuation Layer amounts when stock_account is installed,
        otherwise standard price × qty.
        """
        self.ensure_one()

        if 'stock.valuation.layer' in self.env:
            svl = self.env['stock.valuation.layer'].search([
                ('stock_move_id', 'in', self.move_ids.ids),
            ])
            if svl:
                return abs(sum(svl.mapped('value')))

        total = 0.0
        done_moves = self.move_ids.filtered(lambda m: m.state == 'done')
        moves_to_use = done_moves or self.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
        )
        for move in moves_to_use:
            price = move.product_id.standard_price or 0.0
            qty = (move.quantity if move.state == 'done' else move.product_uom_qty) or 0.0
            total += price * qty
        return total

    def _wh_create_transfer_journal_entry(self, journal, debit_account, credit_account,
                                          amount, ref, picking=None,
                                          debit_analytic=None, credit_analytic=None):
        """
        Create and post a journal entry:
            Dr Stock Transfer In  (receiver analytic)
            Cr Stock Transfer Out (sender analytic)
        """
        company = self.company_id or self.env.company

        debit_line_vals = {
            'name': ref,
            'account_id': debit_account.id,
            'debit': amount,
            'credit': 0.0,
        }
        if debit_analytic:
            debit_line_vals['analytic_distribution'] = {
                str(debit_analytic.id): 100.0,
            }

        credit_line_vals = {
            'name': ref,
            'account_id': credit_account.id,
            'debit': 0.0,
            'credit': amount,
        }
        if credit_analytic:
            credit_line_vals['analytic_distribution'] = {
                str(credit_analytic.id): 100.0,
            }

        move_vals = {
            'ref': ref,
            'journal_id': journal.id,
            'company_id': company.id,
            'line_ids': [
                (0, 0, debit_line_vals),
                (0, 0, credit_line_vals),
            ],
        }
        if picking:
            move_vals['wh_stock_picking_id'] = picking.id

        move = self.env['account.move'].create(move_vals)
        move.action_post()
        return move

    # ── Auto-set wh_send_state on creation ───────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._wh_try_set_pending()
        records._invalidate_picking_type_counts()
        return records

    # ── Auto-set wh_send_state on write ──────────────────────────────────────
    def write(self, vals):
        res = super().write(vals)

        # Re-evaluate cross-WH flag whenever locations, type, or state change.
        # This is the critical fix for replenishment: Odoo's procurement rules
        # often write location_id / location_dest_id AFTER the initial create,
        # so the create() hook sees no locations yet. The write() hook catches
        # that second pass.
        location_fields = {'location_id', 'location_dest_id', 'picking_type_id'}
        state_fields = {'state', 'wh_send_state'}
        if location_fields & vals.keys():
            self._wh_try_set_pending()

        if (location_fields | state_fields) & vals.keys():
            self._invalidate_picking_type_counts()

        return res

    def action_view_wh_accept_journal_entry(self):
        """Open the Accept journal entry in form view."""
        self.ensure_one()
        if not self.wh_accept_journal_entry_id:
            raise UserError(_('No journal entry has been created yet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.wh_accept_journal_entry_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Send action ───────────────────────────────────────────────────────────
    def action_wh_send(self):
        """Mark transfer as sent so the destination WH can accept it."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('Cannot send a completed or cancelled transfer.'))
        if self.wh_send_state != 'pending':
            raise UserError(_(
                'This transfer has already been sent or is not a '
                'cross-warehouse outgoing transfer.'
            ))

        # Reserve stock if not already done
        if self.state in ('confirmed', 'waiting'):
            self.action_assign()

        self.wh_send_state = 'sent'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Sent'),
                'message': _(
                    'Transfer %s has been sent. '
                    'The destination warehouse can now accept it.'
                ) % self.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    # ── Accept action ─────────────────────────────────────────────────────────
    def action_wh_accept(self):
        """Accept and validate this incoming cross-WH transfer.
        Creates a journal entry:
            Dr  Stock Transfer In  (receiver WH analytic)
            Cr  Stock Transfer Out (sender WH analytic)
        """
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            raise UserError(_('Cannot accept a completed or cancelled transfer.'))
        if self.wh_send_state != 'sent':
            raise UserError(_(
                'This transfer must be sent first before it can be accepted.'
            ))

        # Fill in quantity = demand for any unfilled move lines
        for ml in self.move_line_ids:
            if not ml.quantity:
                ml.quantity = ml.reserved_uom_qty or ml.move_id.product_uom_qty

        # For moves with no move lines, set quantity on the move itself
        for move in self.move_ids.filtered(
            lambda m: m.state not in ('done', 'cancel') and not m.move_line_ids
        ):
            move.quantity = move.product_uom_qty

        self.wh_send_state = 'accepted'

        # Validate — skip backorder prompt where possible
        res = self.with_context(skip_backorder=True).button_validate()

        # If Odoo still needs a backorder confirmation, let it through
        if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            return res

        # ── Create journal entry (Accept only) ────────────────────────────────
        src_wh = _resolve_warehouse(self.location_id)
        dst_wh = _resolve_warehouse(self.location_dest_id)
        if src_wh and dst_wh:
            in_acc = dst_wh.wh_stock_transfer_in_account_id
            out_acc = src_wh.wh_stock_transfer_out_account_id
            journal = self._wh_get_journal(dst_wh) or self._wh_get_journal(src_wh)
            debit_analytic = dst_wh.wh_analytic_account_id or False
            credit_analytic = src_wh.wh_analytic_account_id or False

            if in_acc and out_acc and journal:
                amount = self._wh_compute_accept_amount()
                if amount > 0:
                    ref = self.name
                    move = self._wh_create_transfer_journal_entry(
                        journal=journal,
                        debit_account=in_acc,
                        credit_account=out_acc,
                        amount=amount,
                        ref=ref,
                        picking=self,
                        debit_analytic=debit_analytic,
                        credit_analytic=credit_analytic,
                    )
                    self.wh_accept_journal_entry_id = move.id

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Accepted & Validated'),
                'message': _(
                    'Transfer %s has been validated successfully.'
                ) % self.name,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }