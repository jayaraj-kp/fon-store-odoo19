# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    inventory_journal_entry_id = fields.Many2one(
        'account.move',
        string='Inventory Journal Entry',
        readonly=True,
        copy=False,
        help='Journal entry created for this physical inventory adjustment',
    )

    def _is_inventory_adjustment(self):
        """Check if this stock move is a physical inventory adjustment."""
        inventory_loss_loc = self.env.ref(
            'stock.location_inventory', raise_if_not_found=False
        )
        if not inventory_loss_loc:
            return False
        return (
            self.location_id == inventory_loss_loc
            or self.location_dest_id == inventory_loss_loc
        )

    def _get_inventory_journal(self):
        """Get the stock journal from the product category."""
        categ = self.product_id.categ_id
        journal = categ.property_stock_journal
        if not journal:
            raise UserError(_(
                'No Stock Journal found for product category "%s". '
                'Please configure it at: '
                'Inventory > Configuration > Product Categories > %s > Stock Journal'
            ) % (categ.name, categ.name))
        return journal

    def _get_inventory_accounts(self):
        """
        Get debit and credit accounts for the inventory adjustment journal entry.

        For a quantity INCREASE (inventory_loss -> stock):
            DR  Stock Valuation Account  (asset increases)
            CR  Stock Variation Account  (expense/equity offset)

        For a quantity DECREASE (stock -> inventory_loss):
            DR  Stock Variation Account  (expense increases)
            CR  Stock Valuation Account  (asset decreases)
        """
        categ = self.product_id.categ_id
        inventory_loss_loc = self.env.ref('stock.location_inventory')

        stock_valuation_account = categ.property_stock_valuation_account_id
        # Use our custom field first, then fallback to expense account
        stock_variation_account = categ.property_account_creditor_price_difference
        if not stock_variation_account:
            stock_variation_account = categ.property_account_expense_categ_id

        if not stock_valuation_account:
            raise UserError(_(
                'No Stock Valuation Account configured for product category "%s". '
                'Please set it at: '
                'Inventory > Configuration > Product Categories > %s > Stock Valuation Account'
            ) % (categ.name, categ.name))

        if not stock_variation_account:
            raise UserError(_(
                'No Stock Variation Account configured for product category "%s". '
                'Please set it at: '
                'Inventory > Configuration > Product Categories > %s > Stock Variation'
            ) % (categ.name, categ.name))

        # Quantity increase: inventory_loss is source -> goods entering stock
        if self.location_id == inventory_loss_loc:
            debit_account = stock_valuation_account
            credit_account = stock_variation_account
        else:
            # Quantity decrease: inventory_loss is destination -> goods leaving stock
            debit_account = stock_variation_account
            credit_account = stock_valuation_account

        return debit_account, credit_account

    def _compute_inventory_value(self):
        """Compute the monetary value of this inventory adjustment move."""
        qty = self.quantity
        cost = self.product_id.standard_price or 0.0
        if not cost:
            _logger.warning(
                'Product "%s" has no cost price set. Journal entry will have zero value.',
                self.product_id.name
            )
        return qty * cost

    def _create_inventory_journal_entry(self):
        """
        Create accounting journal entry for physical inventory adjustments.
        Called after stock move is validated/done.
        """
        AccountMove = self.env['account.move']

        for move in self:
            if not move._is_inventory_adjustment():
                continue

            categ = move.product_id.categ_id
            if not categ.property_stock_valuation_account_id:
                _logger.info(
                    'Skipping journal entry for product "%s": no stock valuation account configured',
                    move.product_id.name
                )
                continue

            if move.inventory_journal_entry_id:
                _logger.info('Journal entry already exists for move %s, skipping.', move.name)
                continue

            value = move._compute_inventory_value()
            if not value:
                _logger.warning('Skipping journal entry for move %s: computed value is zero.', move.name)
                continue

            try:
                journal = move._get_inventory_journal()
                debit_account, credit_account = move._get_inventory_accounts()
            except UserError as e:
                _logger.error('Cannot create journal entry for move %s: %s', move.name, str(e))
                raise

            move_date = move.date or fields.Date.context_today(move)
            ref = _('Inventory Adjustment: %s') % (move.reference or move.name or '')

            journal_entry_vals = {
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': move_date,
                'ref': ref,
                'company_id': move.company_id.id,
                'line_ids': [
                    (0, 0, {
                        'name': _('Inventory Adj. - %s') % move.product_id.display_name,
                        'account_id': debit_account.id,
                        'debit': value,
                        'credit': 0.0,
                        'quantity': move.quantity,
                        'product_id': move.product_id.id,
                    }),
                    (0, 0, {
                        'name': _('Inventory Adj. - %s') % move.product_id.display_name,
                        'account_id': credit_account.id,
                        'debit': 0.0,
                        'credit': value,
                        'quantity': move.quantity,
                        'product_id': move.product_id.id,
                    }),
                ],
            }

            journal_entry = AccountMove.create(journal_entry_vals)
            journal_entry.action_post()
            move.inventory_journal_entry_id = journal_entry.id

            _logger.info(
                'Created inventory adjustment journal entry %s for stock move %s (product: %s, value: %s)',
                journal_entry.name, move.name, move.product_id.name, value,
            )

        return True

    def action_open_inventory_journal_entry(self):
        """Open the linked inventory adjustment journal entry."""
        self.ensure_one()
        if not self.inventory_journal_entry_id:
            raise UserError(_('No journal entry linked to this inventory adjustment.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inventory Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.inventory_journal_entry_id.id,
        }

    def _action_done(self, cancel_backorder=False):
        """Hook 1: via _action_done (some Odoo 19 flows still use this)."""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        inventory_moves = self.filtered(
            lambda m: m.state == 'done' and m._is_inventory_adjustment()
        )
        if inventory_moves:
            inventory_moves._create_inventory_journal_entry()
        return res


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        """
        Hook 2: Physical Inventory 'Apply' button in Odoo 19 calls
        action_apply_inventory on stock.quant — override here to catch
        the resulting stock moves and create journal entries.
        """
        res = super().action_apply_inventory()

        # After apply, find the most recent inventory adjustment moves
        # for products in this quant set
        inventory_loss_loc = self.env.ref('stock.location_inventory', raise_if_not_found=False)
        if not inventory_loss_loc:
            return res

        product_ids = self.mapped('product_id').ids
        location_ids = self.mapped('location_id').ids

        # Find done moves created just now for these products/locations
        recent_moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            ('product_id', 'in', product_ids),
            '|',
            ('location_id', '=', inventory_loss_loc.id),
            ('location_dest_id', '=', inventory_loss_loc.id),
            ('inventory_journal_entry_id', '=', False),
        ])

        if recent_moves:
            _logger.info(
                'stock_inventory_journal: Found %d inventory adjustment moves after apply, creating journal entries.',
                len(recent_moves)
            )
            recent_moves._create_inventory_journal_entry()

        return res


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_account_creditor_price_difference = fields.Many2one(
        'account.account',
        string='Stock Variation Account',
        company_dependent=True,
        help='Account used as counterpart to Stock Valuation when physical inventory '
             'adjustments are applied (e.g. 610000 Stock Variation).',
    )
