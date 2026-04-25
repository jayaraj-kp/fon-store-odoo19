# -*- coding: utf-8 -*-
"""
account_move.py  [v2 - Fixed for Odoo 19 CE]

Anglo-Saxon inventory accounting for Odoo 19 CE.
Adds missing stock valuation journal lines when vendor bill is confirmed.

WHAT WE ADD on bill confirmation:
    DR  Stock Valuation Account  (110100)
    CR  Stock Input Account      (230300)

Combined with what Odoo already creates:
    DR  Stock Input Account      (230300)
    CR  Account Payable          (211000)

= Full 4-line Anglo-Saxon entry.
"""

import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)

# Odoo 19 CE property_valuation possible internal values — check all
PERPETUAL_VALUES = {'real_time', 'perpetual_invoicing', 'perpetual', 'real_time_invoicing'}


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override action_post to inject Anglo-Saxon lines before posting."""
        for move in self:
            if move.move_type == 'in_invoice' and move.state == 'draft':
                try:
                    added = move._add_anglo_saxon_stock_lines()
                    _logger.info(
                        "Anglo-Saxon v2: Bill %s — added %d valuation line pairs.",
                        move.name or '(draft)', added
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon v2: Failed on bill %s: %s",
                        move.name or '(draft)', str(e), exc_info=True
                    )
        return super().action_post()

    def _is_perpetual_valuation(self, categ):
        """
        Return True if the category uses perpetual (real-time) valuation.
        Checks the raw stored value AND string representation to handle
        Odoo 19 renamed selection keys.
        """
        val = categ.property_valuation
        val_str = str(val).lower()
        _logger.debug("Anglo-Saxon v2: category='%s' property_valuation='%s'", categ.name, val)
        if val in PERPETUAL_VALUES:
            return True
        # Fallback string check in case Odoo 19 renamed the key
        if 'real' in val_str or 'perpetual' in val_str or 'invoic' in val_str:
            return True
        return False

    def _get_stock_accounts_from_category(self, categ):
        """
        Get (valuation_account, input_account) from product category.
        Reads from our custom fields added by stock_account_category_fix module.
        """
        # Our custom fields from stock_account_category_fix
        valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
        input_account = getattr(categ, 'property_stock_account_input_categ_id', False)

        _logger.debug(
            "Anglo-Saxon v2: category='%s' => valuation_acct=%s, input_acct=%s",
            categ.name,
            valuation_account.name if valuation_account else 'NOT SET',
            input_account.name if input_account else 'NOT SET',
        )
        return valuation_account, input_account

    def _get_anglo_saxon_unit_cost(self, invoice_line):
        """
        Get unit cost for stock valuation.
        Priority: FIFO PO price > product standard_price > invoice price_unit
        """
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

    def _add_anglo_saxon_stock_lines(self):
        """
        Add DR Stock Valuation / CR Stock Input lines to this vendor bill.
        Returns number of line pairs added.
        """
        self.ensure_one()
        new_lines_vals = []
        pairs_added = 0

        for inv_line in self.invoice_line_ids.filtered(
            lambda l: l.product_id and not l.display_type
        ):
            product = inv_line.product_id
            categ = product.categ_id

            _logger.debug(
                "Anglo-Saxon v2: line product='%s' categ='%s' valuation='%s' type='%s'",
                product.name, categ.name, categ.property_valuation, product.type
            )

            if not self._is_perpetual_valuation(categ):
                _logger.debug(
                    "Anglo-Saxon v2: SKIP '%s' — valuation='%s' is not perpetual.",
                    product.name, categ.property_valuation
                )
                continue

            valuation_account, input_account = self._get_stock_accounts_from_category(categ)

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon v2: SKIP '%s' — property_stock_valuation_account_id "
                    "is NOT SET on category '%s'. Set it in "
                    "Inventory > Configuration > Product Categories.",
                    product.name, categ.name
                )
                continue

            if not input_account:
                _logger.warning(
                    "Anglo-Saxon v2: SKIP '%s' — property_stock_account_input_categ_id "
                    "is NOT SET on category '%s'.",
                    product.name, categ.name
                )
                continue

            unit_cost = self._get_anglo_saxon_unit_cost(inv_line)
            if unit_cost <= 0.0:
                _logger.warning(
                    "Anglo-Saxon v2: SKIP '%s' — unit cost is zero.",
                    product.name
                )
                continue

            stock_value = unit_cost * inv_line.quantity
            label = _('%s - Stock Valuation') % product.display_name

            _logger.info(
                "Anglo-Saxon v2: ADDING lines for '%s': DR %s %.2f / CR %s %.2f",
                product.name,
                valuation_account.code, stock_value,
                input_account.code, stock_value,
            )

            # DR: Stock Valuation Account (inventory asset increases)
            new_lines_vals.append({
                'move_id': self.id,
                'name': label,
                'account_id': valuation_account.id,
                'debit': stock_value,
                'credit': 0.0,
                'product_id': product.id,
                'product_uom_id': inv_line.product_uom_id.id,
                'quantity': inv_line.quantity,
                'exclude_from_invoice_tab': True,
            })

            # CR: Stock Input Account (GRNI cleared)
            new_lines_vals.append({
                'move_id': self.id,
                'name': label,
                'account_id': input_account.id,
                'debit': 0.0,
                'credit': stock_value,
                'product_id': product.id,
                'product_uom_id': inv_line.product_uom_id.id,
                'quantity': inv_line.quantity,
                'exclude_from_invoice_tab': True,
            })

            pairs_added += 1

        if new_lines_vals:
            self.env['account.move.line'].with_context(
                check_move_validity=False
            ).create(new_lines_vals)

        return pairs_added
