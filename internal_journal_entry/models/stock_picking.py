# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # -----------------------------------------------------------------------
    # Related journal entry (many2one to account.move)
    # -----------------------------------------------------------------------
    internal_transfer_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Internal Transfer Journal Entry',
        copy=False,
        readonly=True,
        ondelete='set null',
    )

    internal_transfer_move_state = fields.Selection(
        related='internal_transfer_move_id.state',
        string='Journal Entry State',
        store=False,
    )

    # -----------------------------------------------------------------------
    # Helper: check if this picking is an internal transfer
    # -----------------------------------------------------------------------
    def _is_internal_transfer(self):
        """Return True if this picking is an internal stock transfer."""
        self.ensure_one()
        return (
            self.picking_type_id
            and self.picking_type_id.code == 'internal'
        )

    # -----------------------------------------------------------------------
    # Main entry-point: called after a picking is validated
    # -----------------------------------------------------------------------
    def _action_done(self):
        """Override to hook journal entry creation after validation."""
        res = super()._action_done()
        for picking in self:
            if picking._is_internal_transfer() and picking.state == 'done':
                try:
                    picking._create_internal_transfer_journal_entry()
                except Exception as e:
                    _logger.error(
                        'Internal Transfer JE creation failed for picking %s: %s',
                        picking.name, str(e)
                    )
        return res

    # -----------------------------------------------------------------------
    # Core: create the journal entry
    # -----------------------------------------------------------------------
    def _create_internal_transfer_journal_entry(self):
        """
        Create a journal entry:
            Stock Transfer A/C  DR   (amount = total product cost)
            Stock Transfer A/C  CR

        Both lines use the SAME account so net effect on the account is zero,
        giving a pure audit trail of the movement.
        """
        self.ensure_one()

        # Avoid duplicates
        if self.internal_transfer_move_id:
            _logger.info(
                'Journal entry already exists for picking %s, skipping.',
                self.name
            )
            return

        # ---- Fetch configuration ----------------------------------------
        company = self.company_id or self.env.company
        config = self.env['res.config.settings']._get_internal_transfer_config(company)

        journal = config.get('journal')
        account = config.get('account')

        if not journal:
            raise UserError(_(
                'No journal configured for Internal Transfer Journal Entries.\n'
                'Please go to Inventory → Configuration → Settings → '
                'Internal Transfer Journal Entry Settings and set a journal.'
            ))
        if not account:
            raise UserError(_(
                'No account configured for Internal Transfer Journal Entries.\n'
                'Please go to Inventory → Configuration → Settings → '
                'Internal Transfer Journal Entry Settings and set an account.'
            ))

        # ---- Compute the transfer amount --------------------------------
        amount = self._get_internal_transfer_amount()

        if amount <= 0:
            _logger.warning(
                'Picking %s has zero/negative cost — journal entry skipped.',
                self.name
            )
            return

        # ---- Build journal entry -----------------------------------------
        move_date = self.date_done or fields.Date.context_today(self)
        ref = _('Internal Transfer: %s') % self.name

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': move_date,
            'ref': ref,
            'company_id': company.id,
            'stock_picking_id': self.id if 'stock_picking_id' in self.env['account.move']._fields else False,
            'line_ids': [
                # Debit line  — Stock Transfer A/C DR
                (0, 0, {
                    'name': _('Stock Transfer - %s (DR)') % self.name,
                    'account_id': account.id,
                    'debit': amount,
                    'credit': 0.0,
                    'partner_id': False,
                    'ref': ref,
                }),
                # Credit line — Stock Transfer A/C CR
                (0, 0, {
                    'name': _('Stock Transfer - %s (CR)') % self.name,
                    'account_id': account.id,
                    'debit': 0.0,
                    'credit': amount,
                    'partner_id': False,
                    'ref': ref,
                }),
            ],
        }

        # Remove stock_picking_id if field not present (safety)
        if not move_vals['stock_picking_id']:
            move_vals.pop('stock_picking_id', None)

        move = self.env['account.move'].sudo().create(move_vals)
        move.sudo().action_post()   # Auto-post the entry

        self.internal_transfer_move_id = move.id
        _logger.info(
            'Created and posted journal entry %s for internal transfer %s',
            move.name, self.name
        )

    # -----------------------------------------------------------------------
    # Helper: compute total cost of the transfer
    # -----------------------------------------------------------------------
    def _get_internal_transfer_amount(self):
        """
        Calculate the total monetary value of the transfer.

        Strategy (in order of preference):
          1. Sum of (qty_done × standard_price) for each move line
          2. Sum of (product_qty × standard_price) for each move
          3. Return 0 so the caller can skip gracefully
        """
        self.ensure_one()
        total = 0.0

        for move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = move.product_id
            if not product:
                continue

            # Use actual done quantity
            qty_done = move.quantity
            if qty_done <= 0:
                qty_done = move.product_qty

            # Cost: prefer standard_price, fall back to 1.0
            cost = product.standard_price or 0.0
            total += qty_done * cost

        # If all standard_price are 0 but we still have moves, use qty × 1
        if total == 0.0 and self.move_ids.filtered(lambda m: m.state == 'done'):
            total = sum(
                m.quantity or m.product_qty
                for m in self.move_ids.filtered(lambda m: m.state == 'done')
            )

        return total

    # -----------------------------------------------------------------------
    # Smart button: open linked journal entry
    # -----------------------------------------------------------------------
    def action_view_internal_transfer_move(self):
        """Open the linked journal entry in form view."""
        self.ensure_one()
        if not self.internal_transfer_move_id:
            raise UserError(_('No journal entry linked to this transfer.'))
        return {
            'name': _('Internal Transfer Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.internal_transfer_move_id.id,
            'target': 'current',
        }
