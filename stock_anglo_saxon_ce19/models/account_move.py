# -*- coding: utf-8 -*-
"""
account_move.py [v5]
Hooks into stock.picking (receipt validation) to create journal entry.
Also fixes vendor bill to add stock valuation lines.
"""
import logging
from odoo import models, api, _
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Add Anglo-Saxon stock valuation lines on vendor bill confirmation."""
        for move in self:
            if move.move_type == 'in_invoice' and move.state == 'draft':
                try:
                    move.invalidate_recordset()
                    added = move._add_anglo_saxon_stock_lines()
                    _logger.info(
                        "Anglo-Saxon v5 (Bill): '%s' — added %d line pairs.",
                        move.name or '(draft)', added
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon v5 (Bill): Failed '%s': %s",
                        move.name or '(draft)', str(e), exc_info=True
                    )
        return super().action_post()

    def _add_anglo_saxon_stock_lines(self):
        self.ensure_one()
        new_lines_vals = []
        pairs_added = 0

        # Odoo 19 removed exclude_from_invoice_tab — use display_type instead
        invoice_lines = self.env['account.move.line'].search([
            ('move_id', '=', self.id),
            ('display_type', '=', 'product'),
            ('product_id', '!=', False),
        ])

        _logger.info(
            "Anglo-Saxon v5 (Bill): id=%s found %d product lines.",
            self.id, len(invoice_lines)
        )

        for inv_line in invoice_lines:
            product = inv_line.product_id
            categ = product.categ_id
            prop_val = categ.property_valuation
            val_str = str(prop_val).lower()

            is_periodic = (
                prop_val in ('manual_periodic', 'periodic', 'at_closing')
                or ('periodic' in val_str and 'invoic' not in val_str)
                or ('closing' in val_str)
            )
            if is_periodic:
                continue

            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            input_account = getattr(categ, 'property_stock_account_input_categ_id', False)

            if not valuation_account or not input_account:
                _logger.warning(
                    "Anglo-Saxon v5 (Bill): SKIP '%s' — accounts not set on '%s'.",
                    product.name, categ.name
                )
                continue

            unit_cost = self._get_unit_cost(inv_line)
            if unit_cost <= 0.0:
                continue

            stock_value = unit_cost * inv_line.quantity
            label = _('%s - Stock Valuation') % product.display_name

            new_lines_vals += [
                {
                    'move_id': self.id,
                    'name': label,
                    'account_id': valuation_account.id,
                    'debit': stock_value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'product_uom_id': inv_line.product_uom_id.id,
                    'quantity': inv_line.quantity,
                    'display_type': 'product',
                },
                {
                    'move_id': self.id,
                    'name': label,
                    'account_id': input_account.id,
                    'debit': 0.0,
                    'credit': stock_value,
                    'product_id': product.id,
                    'product_uom_id': inv_line.product_uom_id.id,
                    'quantity': inv_line.quantity,
                    'display_type': 'product',
                },
            ]
            pairs_added += 1

        if new_lines_vals:
            self.env['account.move.line'].with_context(
                check_move_validity=False
            ).create(new_lines_vals)

        return pairs_added

    def _get_unit_cost(self, invoice_line):
        product = invoice_line.product_id
        cost_method = product.categ_id.property_cost_method
        if cost_method == 'fifo':
            po_line = getattr(invoice_line, 'purchase_line_id', False)
            if po_line and po_line.price_unit > 0:
                price = po_line.price_unit
                if self.currency_id and self.currency_id != self.company_id.currency_id:
                    price = self.currency_id._convert(
                        price, self.company_id.currency_id,
                        self.company_id, self.invoice_date or self.date,
                    )
                return price
        if product.standard_price > 0:
            return product.standard_price
        price = invoice_line.price_unit
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            price = self.currency_id._convert(
                price, self.company_id.currency_id,
                self.company_id, self.invoice_date or self.date,
            )
        return price
