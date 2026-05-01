# -*- coding: utf-8 -*-
"""
pos_account_move.py  [FINAL FIX]

WHY THE PREVIOUS account_move.py DID NOT WORK FOR POS:
=======================================================
Regular invoices (SO → Invoice):
  Odoo calls _get_computed_account() on each line → our override worked.

POS invoices (POS Order → Invoice):
  Odoo 19 POS calls _generate_pos_order_invoice()
    → pos.order._prepare_invoice_line()
        → This does NOT call _get_computed_account() at all.
        → Instead it calls product._get_product_accounts()
          which returns {'stock_output': <account>} but Odoo 19 CE
          without account_anglo_saxon ignores stock_output entirely
          and falls back to stock.valuation.layer or stock_valuation
          account directly.

THE REAL FIX:
=============
Override pos.order._prepare_invoice_line() to inject the correct
stock output account (121200 Stock Interim Delivered) into the
COGS line of the POS invoice.

We hook AFTER the standard _prepare_invoice_line() and replace
the account_id if it matches the stock valuation account.

This is the ONLY reliable interception point for POS invoice lines.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PosOrderInvoiceFix(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_line(self, order_line):
        """
        Override to replace Stock Valuation account (110100) with
        Stock Interim Delivered account (121200) on COGS lines of
        POS invoices.

        Odoo 19 POS creates invoice lines here. The standard code
        sets account_id to the stock_valuation account because
        account_anglo_saxon module is absent in CE.

        We intercept after super() and swap the account if needed.
        """
        vals = super()._prepare_invoice_line(order_line)

        product = order_line.product_id
        if not product:
            return vals

        categ = product.categ_id

        # Only act on perpetual/real_time valuation categories
        val = categ.property_valuation
        if isinstance(val, dict):
            val_str = list(val.values())[0] if val else ''
        else:
            val_str = str(val) if val else ''

        if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
            return vals

        # Get our custom accounts from stock_account_category_fix
        valuation_account = getattr(
            categ, 'property_stock_valuation_account_id', False)
        output_account = getattr(
            categ, 'property_stock_account_output_categ_id', False)

        if not output_account or not valuation_account:
            _logger.warning(
                "POS Invoice Fix: category '%s' missing output or "
                "valuation account. Skipping.", categ.name)
            return vals

        # Check if Odoo placed the stock_valuation account on this line
        current_account_id = vals.get('account_id')
        if current_account_id and current_account_id == valuation_account.id:
            vals['account_id'] = output_account.id
            _logger.info(
                "POS Invoice Fix: product '%s' → replaced account %s (%s)"
                " with %s (%s)",
                product.name,
                valuation_account.code, valuation_account.name,
                output_account.code, output_account.name,
            )

        return vals


class AccountMoveLinePosFix(models.Model):
    """
    Belt-and-suspenders: also fix at the AccountMoveLine level.
    This catches any path that _prepare_invoice_line doesn't cover
    (e.g. invoice lines created programmatically from POS).
    """
    _inherit = 'account.move.line'

    def _get_computed_account(self):
        account = super()._get_computed_account()

        move = self.move_id
        # Only fix customer invoices / credit notes
        if move.move_type not in ('out_invoice', 'out_refund'):
            return account

        product = self.product_id
        if not product or not account:
            return account

        categ = product.categ_id

        # Only perpetual valuation categories
        val = categ.property_valuation
        if isinstance(val, dict):
            val_str = list(val.values())[0] if val else ''
        else:
            val_str = str(val) if val else ''

        if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
            return account

        valuation_account = getattr(
            categ, 'property_stock_valuation_account_id', False)
        output_account = getattr(
            categ, 'property_stock_account_output_categ_id', False)

        if output_account and valuation_account \
                and account.id == valuation_account.id:
            _logger.info(
                "AccountMoveLine Fix: '%s' replacing %s → %s",
                product.name,
                valuation_account.name,
                output_account.name,
            )
            return output_account

        return account