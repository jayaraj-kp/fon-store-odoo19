# -*- coding: utf-8 -*-
"""
account_move.py

Hooks into vendor bill (account.move) confirmation to add the missing
Anglo-Saxon inventory accounting lines in Odoo 19 CE.

When a vendor bill linked to a purchase order is confirmed, Odoo 19 CE
(without account_anglo_saxon) only creates:
    DR  Stock Interim Received   (230300)
    CR  Account Payable          (211000)

This module adds the missing lines:
    DR  Stock Valuation Account  (110100)
    CR  Stock Interim Received   (230300)

Result: Full 4-line Anglo-Saxon journal entry.

Reads accounts from your custom fields on product.category:
    - property_stock_valuation_account_id  (Stock Valuation Account)
    - property_stock_account_input_categ_id (Stock Input Account)
    - property_stock_journal               (Stock Journal)
"""

import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        Override action_post to inject Anglo-Saxon inventory lines
        into vendor bills before they are posted.
        """
        for move in self:
            if move._is_purchase_bill_with_stock():
                move._add_anglo_saxon_stock_lines()
        return super().action_post()

    def _is_purchase_bill_with_stock(self):
        """
        Check if this journal entry is a vendor bill linked to a purchase order
        that has storable products with perpetual valuation.
        """
        self.ensure_one()
        if self.move_type != 'in_invoice':
            return False
        if self.state != 'draft':
            return False
        # Check if any invoice line has a product with real_time valuation
        for line in self.invoice_line_ids.filtered(lambda l: l.product_id):
            product = line.product_id
            categ = product.categ_id
            if categ.property_valuation == 'real_time':
                # Check our custom stock valuation account field exists and is set
                if hasattr(categ, 'property_stock_valuation_account_id') and \
                        categ.property_stock_valuation_account_id:
                    return True
        return False

    def _add_anglo_saxon_stock_lines(self):
        """
        Add the Anglo-Saxon inventory accounting lines to the vendor bill.

        For each invoice line with a storable product (perpetual valuation):
            DR  Stock Valuation Account  (inventory increases on balance sheet)
            CR  Stock Input Account      (GRNI account cleared)

        These lines are added to the existing move lines BEFORE posting.
        The lines use the accounts from your custom product category fields:
            - property_stock_valuation_account_id
            - property_stock_account_input_categ_id
        """
        self.ensure_one()
        new_lines_vals = []

        for inv_line in self.invoice_line_ids.filtered(
            lambda l: l.product_id and not l.display_type
        ):
            product = inv_line.product_id
            categ = product.categ_id

            # Only process products with perpetual (real_time) valuation
            if categ.property_valuation != 'real_time':
                continue

            # Get accounts from your custom fields
            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            input_account = getattr(categ, 'property_stock_account_input_categ_id', False)

            if not valuation_account:
                _logger.warning(
                    "No Stock Valuation Account on category '%s' for product '%s'. "
                    "Skipping Anglo-Saxon lines.",
                    categ.name, product.name
                )
                continue

            if not input_account:
                _logger.warning(
                    "No Stock Input Account on category '%s' for product '%s'. "
                    "Skipping Anglo-Saxon lines.",
                    categ.name, product.name
                )
                continue

            # Calculate the stock value using the unit cost * qty
            # Use the product's current cost (AVCO/Standard) or PO line price (FIFO)
            unit_cost = self._get_anglo_saxon_unit_cost(inv_line)
            if unit_cost <= 0.0:
                _logger.info(
                    "Zero cost for product '%s', skipping Anglo-Saxon lines.", product.name
                )
                continue

            quantity = inv_line.quantity
            stock_value = unit_cost * quantity

            label = _('%(product)s - Stock Valuation (Anglo-Saxon)',
                      product=product.display_name)

            # Line 1: DR Stock Valuation Account (inventory asset increases)
            new_lines_vals.append({
                'move_id': self.id,
                'name': label,
                'account_id': valuation_account.id,
                'debit': stock_value,
                'credit': 0.0,
                'product_id': product.id,
                'product_uom_id': inv_line.product_uom_id.id,
                'quantity': quantity,
                'exclude_from_invoice_tab': True,
            })

            # Line 2: CR Stock Input Account (GRNI cleared)
            new_lines_vals.append({
                'move_id': self.id,
                'name': label,
                'account_id': input_account.id,
                'debit': 0.0,
                'credit': stock_value,
                'product_id': product.id,
                'product_uom_id': inv_line.product_uom_id.id,
                'quantity': quantity,
                'exclude_from_invoice_tab': True,
            })

        if new_lines_vals:
            # Check for duplicate Anglo-Saxon lines (avoid re-adding if already present)
            existing_labels = self.line_ids.mapped('name')
            filtered_vals = []
            seen = set()
            for vals in new_lines_vals:
                key = (vals['account_id'], vals['debit'], vals['credit'], vals['product_id'])
                if key not in seen:
                    # Only add if this exact combination doesn't already exist
                    already_exists = self.line_ids.filtered(
                        lambda l: l.account_id.id == vals['account_id']
                        and abs(l.debit - vals['debit']) < 0.01
                        and abs(l.credit - vals['credit']) < 0.01
                        and l.product_id.id == vals['product_id']
                        and 'Anglo-Saxon' in (l.name or '')
                    )
                    if not already_exists:
                        filtered_vals.append(vals)
                        seen.add(key)

            if filtered_vals:
                self.env['account.move.line'].with_context(
                    check_move_validity=False
                ).create(filtered_vals)
                _logger.info(
                    "Added %d Anglo-Saxon stock lines to bill %s",
                    len(filtered_vals), self.name
                )

    def _get_anglo_saxon_unit_cost(self, invoice_line):
        """
        Determine the unit cost for the Anglo-Saxon stock valuation line.

        Priority:
        1. FIFO: use the price from the linked purchase order line
        2. AVCO / Standard: use the product's current standard_price
        3. Fallback: use the invoice line's price_unit

        Args:
            invoice_line: account.move.line record (invoice line)

        Returns:
            float: unit cost to use for stock valuation
        """
        product = invoice_line.product_id
        categ = product.categ_id
        cost_method = categ.property_cost_method

        if cost_method == 'fifo':
            # For FIFO: try to get the actual PO line price
            purchase_line = invoice_line.purchase_line_id
            if purchase_line:
                price = purchase_line.price_unit
                # Convert currency if needed
                if self.currency_id != self.company_id.currency_id:
                    price = self.currency_id._convert(
                        price,
                        self.company_id.currency_id,
                        self.company_id,
                        self.invoice_date or self.date,
                    )
                return price

        if cost_method in ('average', 'standard'):
            # For AVCO and Standard: use the product's current cost
            cost = product.standard_price
            if cost > 0:
                return cost

        # Final fallback: use the invoice line price
        price = invoice_line.price_unit
        # Convert currency if needed
        if self.currency_id != self.company_id.currency_id:
            price = self.currency_id._convert(
                price,
                self.company_id.currency_id,
                self.company_id,
                self.invoice_date or self.date,
            )
        return price
