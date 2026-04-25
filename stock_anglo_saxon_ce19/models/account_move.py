# -*- coding: utf-8 -*-
"""
account_move.py  [v3 - Debug + All valuation values]
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
                    added = move._add_anglo_saxon_stock_lines()
                    _logger.info(
                        "Anglo-Saxon v3: Bill '%s' — added %d valuation line pairs.",
                        move.name or '(draft)', added
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon v3: Failed on bill '%s': %s",
                        move.name or '(draft)', str(e), exc_info=True
                    )
        return super().action_post()

    def _add_anglo_saxon_stock_lines(self):
        """
        Add DR Stock Valuation / CR Stock Input lines to this vendor bill.
        Returns number of line pairs added.
        """
        self.ensure_one()
        new_lines_vals = []
        pairs_added = 0

        invoice_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id and not l.display_type
        )

        _logger.info(
            "Anglo-Saxon v3: Bill '%s' has %d invoice lines to check.",
            self.name or '(draft)', len(invoice_lines)
        )

        for inv_line in invoice_lines:
            product = inv_line.product_id
            categ = product.categ_id

            # ---- FULL DEBUG: log everything ----
            prop_val = categ.property_valuation
            prop_cost = categ.property_cost_method
            prod_type = product.type

            _logger.info(
                "Anglo-Saxon v3: LINE => product='%s', type='%s', "
                "category='%s', property_valuation='%s' (type=%s), "
                "property_cost_method='%s'",
                product.name, prod_type,
                categ.name, prop_val, type(prop_val).__name__,
                prop_cost,
            )

            # Log our custom fields
            val_acct = getattr(categ, 'property_stock_valuation_account_id', 'FIELD_MISSING')
            inp_acct = getattr(categ, 'property_stock_account_input_categ_id', 'FIELD_MISSING')
            _logger.info(
                "Anglo-Saxon v3: ACCOUNTS => valuation_account=%s, input_account=%s",
                val_acct.name if hasattr(val_acct, 'name') and val_acct else val_acct,
                inp_acct.name if hasattr(inp_acct, 'name') and inp_acct else inp_acct,
            )

            # ---- Check valuation — accept ALL known perpetual values ----
            # Odoo 19 CE changed the internal key. Log it and accept anything non-periodic.
            val_str = str(prop_val).lower()
            is_perpetual = (
                prop_val in ('real_time', 'perpetual_invoicing', 'perpetual',
                             'real_time_invoicing', 'invoicing')
                or 'real' in val_str
                or 'perpetual' in val_str
                or 'invoic' in val_str
            )

            # Also accept if it's NOT periodic (exclude only explicit periodic)
            is_periodic = prop_val in ('manual_periodic', 'periodic', 'closing', 'at_closing')
            if not is_periodic and prop_val not in ('', False, None):
                # If it's not explicitly periodic AND it's set — treat as perpetual
                _logger.info(
                    "Anglo-Saxon v3: '%s' valuation='%s' => "
                    "is_perpetual=%s, is_periodic=%s => ACCEPTING as perpetual.",
                    product.name, prop_val, is_perpetual, is_periodic
                )
                is_perpetual = True

            if not is_perpetual:
                _logger.info(
                    "Anglo-Saxon v3: SKIP '%s' — valuation='%s' is periodic.",
                    product.name, prop_val
                )
                continue

            # ---- Get accounts ----
            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            input_account = getattr(categ, 'property_stock_account_input_categ_id', False)

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon v3: SKIP '%s' — Stock Valuation Account NOT SET "
                    "on category '%s'.", product.name, categ.name
                )
                continue

            if not input_account:
                _logger.warning(
                    "Anglo-Saxon v3: SKIP '%s' — Stock Input Account NOT SET "
                    "on category '%s'.", product.name, categ.name
                )
                continue

            # ---- Get cost ----
            unit_cost = self._get_unit_cost(inv_line)
            _logger.info(
                "Anglo-Saxon v3: COST => product='%s', method='%s', "
                "standard_price=%s, invoice_price=%s, computed_cost=%s",
                product.name, prop_cost,
                product.standard_price, inv_line.price_unit, unit_cost,
            )

            if unit_cost <= 0.0:
                _logger.warning(
                    "Anglo-Saxon v3: SKIP '%s' — unit cost is zero or negative.",
                    product.name
                )
                continue

            stock_value = unit_cost * inv_line.quantity
            label = _('%s - Stock Valuation') % product.display_name

            _logger.info(
                "Anglo-Saxon v3: CREATING LINES => '%s' qty=%s cost=%s value=%s "
                "DR=%s CR=%s",
                product.name, inv_line.quantity, unit_cost, stock_value,
                valuation_account.code, input_account.code,
            )

            # DR: Stock Valuation Account
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

            # CR: Stock Input Account
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
            _logger.info(
                "Anglo-Saxon v3: Successfully created %d lines on bill '%s'.",
                len(new_lines_vals), self.name or '(draft)'
            )

        return pairs_added

    def _get_unit_cost(self, invoice_line):
        """Get unit cost: FIFO=PO price, AVCO/Std=standard_price, fallback=invoice price"""
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
