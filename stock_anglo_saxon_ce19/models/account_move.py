# -*- coding: utf-8 -*-
"""
account_move.py

Fixes the customer invoice COGS line to use Stock Output Account (121200
Stock Interim Delivered) instead of Stock Valuation (110100).

ROOT CAUSE (Odoo 19 CE):
    Odoo 19 removed account_anglo_saxon. When a customer invoice is confirmed,
    the COGS line account falls back to the stock_valuation account (110100)
    instead of the correct stock_output/interim-delivered account (121200).

    For POS invoices created at SESSION CLOSING:
        pos.session._create_account_move() builds invoice line_ids with raw
        account IDs, completely bypassing pos.order._prepare_invoice_line()
        and account.move.line._get_computed_account() (which only fires on
        onchange). Overriding those methods does NOT fix POS session invoices.

    THE CORRECT FIX:
        Override account.move.line.create() — this fires for ALL invoice line
        creation paths: session-based, order-based, and manual invoices.

TWO-LAYER DEFENCE:
    1. ProductTemplate.get_product_accounts() — injects correct accounts into
       the accounts dict used by standard SO invoice flow.
    2. AccountMoveLine.create() — intercepts raw account_id in vals_list before
       DB insert; catches session-closing path that bypasses layer 1.
    3. AccountMoveLine._get_computed_account() — belt-and-suspenders for
       draft/onchange flows in the UI.
"""
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

PERPETUAL_VALUES = frozenset({'real_time', 'perpetual', 'perpetual_invoicing'})


def _get_valuation_str(categ):
    """
    Extract the string value of property_valuation.
    Handles Odoo 19 JSONB format: {"1": "real_time"} and plain string.
    """
    val = categ.property_valuation
    if not val:
        return ''
    if isinstance(val, dict):
        return next(iter(val.values()), '') if val else ''
    return str(val)


# ── FIX 1: get_product_accounts ─────────────────────────────────────────────
# Used by standard SO invoice flow (account.move._get_anglo_saxon_price_unit,
# stock_account, purchase_stock). Injects correct accounts into the dict.
# ────────────────────────────────────────────────────────────────────────────
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        """
        Inject our custom stock accounts so that standard Odoo invoice
        generation picks up the correct stock_output / stock_input /
        stock_valuation accounts from the product category.
        """
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
        categ = self.categ_id

        output_account = getattr(categ, 'property_stock_account_output_categ_id', False)
        input_account = getattr(categ, 'property_stock_account_input_categ_id', False)
        valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)

        if output_account:
            accounts['stock_output'] = output_account
            _logger.debug(
                "get_product_accounts '%s': stock_output → %s",
                self.name, output_account.code,
            )
        if input_account:
            accounts['stock_input'] = input_account
            _logger.debug(
                "get_product_accounts '%s': stock_input → %s",
                self.name, input_account.code,
            )
        if valuation_account:
            accounts['stock_valuation'] = valuation_account
            _logger.debug(
                "get_product_accounts '%s': stock_valuation → %s",
                self.name, valuation_account.code,
            )
        return accounts


# ── FIX 2 + 3: AccountMoveLine intercept ────────────────────────────────────
# Replaces stock valuation account (110100) with stock output account (121200)
# on ALL customer invoice lines, regardless of creation path.
# ────────────────────────────────────────────────────────────────────────────
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        FIX 2: Intercept raw account_id in vals_list before DB insert.

        This fires for ALL invoice line creation paths including:
          - pos.session._create_account_move() (session closing)
          - standard SO invoicing
          - manual customer invoice creation

        If a customer invoice line is being created with the Stock Valuation
        account (110100), replace it with the Stock Output/Interim Delivered
        account (121200).
        """
        for vals in vals_list:
            account_id = vals.get('account_id')
            product_id = vals.get('product_id')
            move_id = vals.get('move_id')

            if not (account_id and product_id and move_id):
                continue

            move = self.env['account.move'].browse(move_id)
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue

            product = self.env['product.product'].browse(product_id)
            categ = product.categ_id

            if _get_valuation_str(categ) not in PERPETUAL_VALUES:
                continue

            val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
            out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)

            if not val_acct or not out_acct:
                continue
            if val_acct.id == out_acct.id:
                # Accounts are the same — no action needed
                continue

            if account_id == val_acct.id:
                vals['account_id'] = out_acct.id
                _logger.info(
                    "Anglo-Saxon create() fix: move=%s product='%s' category='%s' "
                    "valuation='%s'  replaced %s (%s) → %s (%s)",
                    move.name or move_id,
                    product.name,
                    categ.name,
                    _get_valuation_str(categ),
                    val_acct.code, val_acct.name,
                    out_acct.code, out_acct.name,
                )

        return super().create(vals_list)

    def _get_computed_account(self):
        """
        FIX 3: Belt-and-suspenders for onchange / draft invoice UI flows.

        _get_computed_account() fires when a user adds a product to a draft
        invoice in the UI. create() handles the programmatic path; this
        handles the interactive path.
        """
        account = super()._get_computed_account()

        move = self.move_id
        if move.move_type not in ('out_invoice', 'out_refund'):
            return account

        product = self.product_id
        if not product or not account:
            return account

        categ = product.categ_id
        if _get_valuation_str(categ) not in PERPETUAL_VALUES:
            return account

        val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
        out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)

        if out_acct and val_acct and account.id == val_acct.id:
            _logger.info(
                "Anglo-Saxon _get_computed_account fix: product='%s' %s → %s",
                product.name, val_acct.code, out_acct.code,
            )
            return out_acct

        return account
