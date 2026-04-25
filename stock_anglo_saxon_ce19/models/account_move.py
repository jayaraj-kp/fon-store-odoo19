# -*- coding: utf-8 -*-
"""
account_move.py  [v4 - Fix: read lines fresh from DB]

Root cause found: When action_post() is called, Odoo 19 has already
committed the bill lines via a separate web_save call. The ORM recordset
in action_post() has a stale cache showing 0 invoice_line_ids.

Fix: Force a cache invalidation before reading invoice lines.
"""

import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Override action_post to inject Anglo-Saxon lines before posting."""
        for move in self:
            if move.move_type == 'in_invoice' and move.state == 'draft':
                try:
                    # CRITICAL FIX: invalidate ORM cache so we read fresh from DB
                    move.invalidate_recordset()
                    move.env.cr.flush()

                    added = move._add_anglo_saxon_stock_lines()
                    _logger.info(
                        "Anglo-Saxon v4: Bill '%s' — added %d valuation line pairs.",
                        move.name or '(draft)', added
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon v4: Failed on bill '%s': %s",
                        move.name or '(draft)', str(e), exc_info=True
                    )
        return super().action_post()

    def _add_anglo_saxon_stock_lines(self):
        """
        Add DR Stock Valuation / CR Stock Input lines to this vendor bill.
        Reads invoice lines fresh from DB to avoid stale ORM cache.
        Returns number of line pairs added.
        """
        self.ensure_one()
        new_lines_vals = []
        pairs_added = 0

        # Read invoice lines fresh from DB using a direct search
        invoice_lines = self.env['account.move.line'].search([
            ('move_id', '=', self.id),
            ('display_type', 'not in', ['line_section', 'line_note']),
            ('product_id', '!=', False),
            ('exclude_from_invoice_tab', '=', False),
        ])

        _logger.info(
            "Anglo-Saxon v4: Bill id=%s '%s' — found %d invoice lines in DB.",
            self.id, self.name or '(draft)', len(invoice_lines)
        )

        for inv_line in invoice_lines:
            product = inv_line.product_id
            categ = product.categ_id

            prop_val = categ.property_valuation
            prop_cost = categ.property_cost_method

            _logger.info(
                "Anglo-Saxon v4: LINE product='%s' categ='%s' "
                "valuation='%s' cost_method='%s' type='%s'",
                product.name, categ.name, prop_val, prop_cost, product.type
            )

            # Get our custom accounts
            valuation_account = getattr(
                categ, 'property_stock_valuation_account_id', False
            )
            input_account = getattr(
                categ, 'property_stock_account_input_categ_id', False
            )

            _logger.info(
                "Anglo-Saxon v4: ACCOUNTS valuation=%s input=%s",
                valuation_account.name if valuation_account else 'NOT SET',
                input_account.name if input_account else 'NOT SET',
            )

            # Skip periodic valuation
            val_str = str(prop_val).lower()
            is_periodic = (
                prop_val in ('manual_periodic', 'periodic', 'at_closing')
                or ('periodic' in val_str and 'invoic' not in val_str)
                or ('closing' in val_str)
            )
            if is_periodic:
                _logger.info(
                    "Anglo-Saxon v4: SKIP '%s' — periodic valuation '%s'.",
                    product.name, prop_val
                )
                continue

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon v4: SKIP '%s' — Stock Valuation Account NOT SET "
                    "on category '%s'.", product.name, categ.name
                )
                continue

            if not input_account:
                _logger.warning(
                    "Anglo-Saxon v4: SKIP '%s' — Stock Input Account NOT SET "
                    "on category '%s'.", product.name, categ.name
                )
                continue

            unit_cost = self._get_unit_cost(inv_line)
            _logger.info(
                "Anglo-Saxon v4: COST product='%s' standard_price=%s "
                "invoice_price=%s computed=%s",
                product.name, product.standard_price,
                inv_line.price_unit, unit_cost
            )

            if unit_cost <= 0.0:
                _logger.warning(
                    "Anglo-Saxon v4: SKIP '%s' — unit cost is zero.", product.name
                )
                continue

            qty = inv_line.quantity
            stock_value = unit_cost * qty
            label = _('%s - Stock Valuation') % product.display_name

            _logger.info(
                "Anglo-Saxon v4: CREATING LINES product='%s' qty=%s "
                "cost=%s value=%s DR=%s CR=%s",
                product.name, qty, unit_cost, stock_value,
                valuation_account.code, input_account.code
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
                'quantity': qty,
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
                'quantity': qty,
                'exclude_from_invoice_tab': True,
            })

            pairs_added += 1

        if new_lines_vals:
            self.env['account.move.line'].with_context(
                check_move_validity=False
            ).create(new_lines_vals)
            _logger.info(
                "Anglo-Saxon v4: Created %d lines on bill '%s'.",
                len(new_lines_vals), self.name or '(draft)'
            )

        return pairs_added

    def _get_unit_cost(self, invoice_line):
        """
        Get unit cost for the stock valuation line.
        Priority: FIFO=PO price > AVCO/Standard=standard_price > invoice price
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
