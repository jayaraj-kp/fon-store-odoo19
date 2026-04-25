# -*- coding: utf-8 -*-
"""
stock_picking.py [v5]

Creates a journal entry when a PURCHASE RECEIPT is validated.

Journal Entry on receipt validation:
    DR  Stock Valuation Account  (110100 - Inventory Asset)
    CR  Stock Input Account      (230300 - GRNI / Stock Interim Received)

This is the "Odoo 18 style" behavior that was removed in Odoo 19 CE.
Reads accounts from custom fields added by stock_account_category_fix module:
    - property_stock_valuation_account_id
    - property_stock_account_input_categ_id
    - property_stock_journal
"""
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    receipt_journal_entry_ids = fields.Many2many(
        comodel_name='account.move',
        relation='stock_picking_anglo_saxon_move_rel',
        column1='picking_id',
        column2='move_id',
        string='Receipt Journal Entries',
        copy=False,
        readonly=True,
    )
    receipt_journal_entry_count = fields.Integer(
        compute='_compute_receipt_journal_entry_count',
        string='Journal Entries',
    )

    @api.depends('receipt_journal_entry_ids')
    def _compute_receipt_journal_entry_count(self):
        for rec in self:
            rec.receipt_journal_entry_count = len(rec.receipt_journal_entry_ids)

    def button_validate(self):
        """Override to create journal entry after receipt validation."""
        res = super().button_validate()
        for picking in self:
            if (picking.state == 'done'
                    and picking.picking_type_code == 'incoming'
                    and not picking.receipt_journal_entry_ids):
                try:
                    picking._create_receipt_valuation_entry()
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon v5 (Receipt): Failed for picking '%s': %s",
                        picking.name, str(e), exc_info=True
                    )
        return res

    def _create_receipt_valuation_entry(self):
        """
        Create the stock valuation journal entry for this receipt.

        DR  Stock Valuation Account   (inventory asset increases)
        CR  Stock Input Account        (GRNI — cleared later by vendor bill)
        """
        self.ensure_one()
        line_vals = []

        for stock_move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = stock_move.product_id
            categ = product.categ_id
            prop_val = categ.property_valuation
            val_str = str(prop_val).lower()

            _logger.info(
                "Anglo-Saxon v5 (Receipt): picking='%s' product='%s' "
                "valuation='%s' cost_method='%s'",
                self.name, product.name, prop_val,
                categ.property_cost_method
            )

            # Skip periodic valuation
            is_periodic = (
                prop_val in ('manual_periodic', 'periodic', 'at_closing')
                or ('periodic' in val_str and 'invoic' not in val_str)
                or ('closing' in val_str)
            )
            if is_periodic:
                _logger.info(
                    "Anglo-Saxon v5 (Receipt): SKIP '%s' — periodic valuation.",
                    product.name
                )
                continue

            # Get accounts from our custom fields
            valuation_account = getattr(
                categ, 'property_stock_valuation_account_id', False
            )
            input_account = getattr(
                categ, 'property_stock_account_input_categ_id', False
            )

            _logger.info(
                "Anglo-Saxon v5 (Receipt): ACCOUNTS valuation=%s input=%s",
                valuation_account.name if valuation_account else 'NOT SET',
                input_account.name if input_account else 'NOT SET',
            )

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon v5 (Receipt): SKIP '%s' — Stock Valuation Account "
                    "not set on category '%s'.", product.name, categ.name
                )
                continue

            if not input_account:
                _logger.warning(
                    "Anglo-Saxon v5 (Receipt): SKIP '%s' — Stock Input Account "
                    "not set on category '%s'.", product.name, categ.name
                )
                continue

            # Get unit cost
            unit_cost = self._get_receipt_unit_cost(stock_move)
            qty = stock_move.product_uom_qty
            stock_value = unit_cost * qty

            _logger.info(
                "Anglo-Saxon v5 (Receipt): product='%s' qty=%s cost=%s value=%s",
                product.name, qty, unit_cost, stock_value
            )

            if stock_value <= 0.0:
                _logger.warning(
                    "Anglo-Saxon v5 (Receipt): SKIP '%s' — zero value.", product.name
                )
                continue

            desc = _('%(picking)s - %(product)s') % {
                'picking': self.name,
                'product': product.display_name,
            }

            # DR: Stock Valuation Account
            line_vals.append({
                'name': desc,
                'account_id': valuation_account.id,
                'debit': stock_value,
                'credit': 0.0,
                'product_id': product.id,
                'product_uom_id': stock_move.product_uom.id,
                'quantity': qty,
            })

            # CR: Stock Input Account (GRNI)
            line_vals.append({
                'name': desc,
                'account_id': input_account.id,
                'debit': 0.0,
                'credit': stock_value,
                'product_id': product.id,
                'product_uom_id': stock_move.product_uom.id,
                'quantity': qty,
            })

        if not line_vals:
            _logger.info(
                "Anglo-Saxon v5 (Receipt): No lines to post for '%s'.", self.name
            )
            return

        # Get stock journal
        journal = self._get_stock_journal()
        if not journal:
            _logger.warning(
                "Anglo-Saxon v5 (Receipt): No stock journal found for '%s'. "
                "Set Stock Journal on product category.", self.name
            )
            return

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Stock Valuation: %s') % self.name,
            'line_ids': [(0, 0, v) for v in line_vals],
            'company_id': self.company_id.id,
        })
        entry.action_post()
        self.receipt_journal_entry_ids = [(4, entry.id)]

        _logger.info(
            "Anglo-Saxon v5 (Receipt): Created & posted entry '%s' for picking '%s'.",
            entry.name, self.name
        )

    def _get_receipt_unit_cost(self, stock_move):
        """Get unit cost for receipt: PO price (FIFO) or standard_price (AVCO/Std)."""
        product = stock_move.product_id
        cost_method = product.categ_id.property_cost_method

        if cost_method == 'fifo':
            po_line = getattr(stock_move, 'purchase_line_id', False)
            if po_line and po_line.price_unit > 0:
                return po_line.price_unit

        return product.standard_price or 0.0

    def _get_stock_journal(self):
        """Get the stock journal: from category or fallback search."""
        for move in self.move_ids.filtered(lambda m: m.state == 'done'):
            categ = move.product_id.categ_id
            journal = getattr(categ, 'property_stock_journal', False)
            if journal:
                return journal

        return self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('name', 'ilike', 'Stock'),
            ('company_id', '=', self.company_id.id),
        ], limit=1) or self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def action_view_receipt_journal_entries(self):
        """Smart button: open related journal entries."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.receipt_journal_entry_ids.ids)],
            'context': {'default_move_type': 'entry'},
        }
