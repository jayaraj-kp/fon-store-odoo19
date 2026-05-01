# # # -*- coding: utf-8 -*-
# # """
# # account_move.py [v7]
# #
# # Fixes the customer invoice COGS entry to use the correct
# # Stock Output Account (121200 Stock Interim Delivered)
# # instead of Stock Valuation (110100).
# #
# # When Odoo 19 confirms a customer invoice, it creates:
# #     DR  600000 Expenses (COGS)
# #     CR  ??? Stock account
# #
# # It reads the stock account from product_tmpl_id.get_product_accounts()
# # which looks for 'stock_output' key. In Odoo 19 CE without account_anglo_saxon,
# # this falls back to the stock valuation account.
# #
# # This module overrides get_product_accounts() on product.template to
# # inject the correct output account from our custom category field.
# # """
# # import logging
# # from odoo import models, api
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class ProductTemplate(models.Model):
# #     _inherit = 'product.template'
# #
# #     def get_product_accounts(self, fiscal_pos=None):
# #         """
# #         Override to inject the correct stock output account
# #         from our custom field property_stock_account_output_categ_id.
# #         """
# #         accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
# #
# #         categ = self.categ_id
# #         output_account = getattr(
# #             categ, 'property_stock_account_output_categ_id', False)
# #         valuation_account = getattr(
# #             categ, 'property_stock_valuation_account_id', False)
# #         input_account = getattr(
# #             categ, 'property_stock_account_input_categ_id', False)
# #
# #         if output_account:
# #             accounts['stock_output'] = output_account
# #             _logger.debug(
# #                 "Anglo-Saxon v7: get_product_accounts '%s' "
# #                 "stock_output => %s", self.name, output_account.name)
# #
# #         if valuation_account:
# #             accounts['stock_valuation'] = valuation_account
# #             _logger.debug(
# #                 "Anglo-Saxon v7: get_product_accounts '%s' "
# #                 "stock_valuation => %s", self.name, valuation_account.name)
# #
# #         if input_account:
# #             accounts['stock_input'] = input_account
# #             _logger.debug(
# #                 "Anglo-Saxon v7: get_product_accounts '%s' "
# #                 "stock_input => %s", self.name, input_account.name)
# #
# #         return accounts
# #
# #
# # # At bottom of account_move.py, add this new class:
# #
# # class AccountMoveLine(models.Model):
# #     _inherit = 'account.move.line'
# #
# #     def _get_computed_account(self):
# #         """
# #         Odoo 19 CE: Override to use stock_output account (121200)
# #         instead of stock_valuation (110100) for COGS lines on invoices.
# #         """
# #         account = super()._get_computed_account()
# #
# #         move = self.move_id
# #         if move.move_type not in ('out_invoice', 'out_refund'):
# #             return account
# #
# #         product = self.product_id
# #         if not product:
# #             return account
# #
# #         categ = product.categ_id
# #         val = categ.property_valuation
# #
# #         # Check if perpetual valuation (handle JSONB dict)
# #         if isinstance(val, dict):
# #             val_str = list(val.values())[0] if val else ''
# #         else:
# #             val_str = str(val) if val else ''
# #
# #         if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
# #             return account
# #
# #         valuation_account = getattr(
# #             categ, 'property_stock_valuation_account_id', False)
# #         output_account = getattr(
# #             categ, 'property_stock_account_output_categ_id', False)
# #
# #         # If current account is stock valuation, replace with stock output
# #         if output_account and valuation_account \
# #                 and account == valuation_account:
# #             _logger.info(
# #                 "Anglo-Saxon invoice fix: replacing %s with %s for '%s'",
# #                 valuation_account.name, output_account.name, product.name
# #             )
# #             return output_account
# #
# #         return account
# #
# # class AccountMoveLine(models.Model):
# #     _inherit = 'account.move.line'
# #
# #     def _get_computed_account(self):
# #         """
# #         Odoo 19 CE: For customer invoices, replace Stock Valuation (110100)
# #         with Stock Output/Interim Delivered (121200) on COGS lines.
# #         """
# #         account = super()._get_computed_account()
# #
# #         move = self.move_id
# #         if move.move_type not in ('out_invoice', 'out_refund'):
# #             return account
# #
# #         product = self.product_id
# #         if not product:
# #             return account
# #
# #         categ = product.categ_id
# #
# #         # Handle Odoo 19 JSONB format: {"1": "real_time"}
# #         val = categ.property_valuation
# #         if isinstance(val, dict):
# #             val_str = list(val.values())[0] if val else ''
# #         else:
# #             val_str = str(val) if val else ''
# #
# #         if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
# #             return account
# #
# #         valuation_account = getattr(
# #             categ, 'property_stock_valuation_account_id', False)
# #         output_account = getattr(
# #             categ, 'property_stock_account_output_categ_id', False)
# #
# #         # Replace stock valuation account with stock output account
# #         if output_account and valuation_account \
# #                 and account and account.id == valuation_account.id:
# #             _logger.info(
# #                 "Anglo-Saxon invoice fix: '%s' replacing %s → %s",
# #                 product.name,
# #                 valuation_account.name,
# #                 output_account.name
# #             )
# #             return output_account
# #
# #         return account
# # -*- coding: utf-8 -*-
# """
# account_move.py [v8]
#
# Fixes the customer invoice COGS entry to use the correct
# Stock Output Account (121200 Stock Interim Delivered)
# instead of Stock Valuation (110100).
# """
# import logging
# from odoo import models, api
#
# _logger = logging.getLogger(__name__)
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     def get_product_accounts(self, fiscal_pos=None):
#         """
#         Override to inject the correct stock output account
#         from our custom field property_stock_account_output_categ_id.
#         """
#         accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
#
#         categ = self.categ_id
#         output_account = getattr(
#             categ, 'property_stock_account_output_categ_id', False)
#         valuation_account = getattr(
#             categ, 'property_stock_valuation_account_id', False)
#         input_account = getattr(
#             categ, 'property_stock_account_input_categ_id', False)
#
#         if output_account:
#             accounts['stock_output'] = output_account
#             _logger.debug(
#                 "Anglo-Saxon v8: get_product_accounts '%s' "
#                 "stock_output => %s", self.name, output_account.name)
#
#         if valuation_account:
#             accounts['stock_valuation'] = valuation_account
#             _logger.debug(
#                 "Anglo-Saxon v8: get_product_accounts '%s' "
#                 "stock_valuation => %s", self.name, valuation_account.name)
#
#         if input_account:
#             accounts['stock_input'] = input_account
#             _logger.debug(
#                 "Anglo-Saxon v8: get_product_accounts '%s' "
#                 "stock_input => %s", self.name, input_account.name)
#
#         return accounts
#
#
# # NOTE: Only ONE AccountMoveLine class — the previous version had a duplicate
# # which caused the first definition to be silently overwritten by Python.
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     def _get_computed_account(self):
#         """
#         Odoo 19 CE: For customer invoices, replace Stock Valuation (110100)
#         with Stock Output/Interim Delivered (121200) on COGS lines.
#         """
#         account = super()._get_computed_account()
#
#         move = self.move_id
#         if move.move_type not in ('out_invoice', 'out_refund'):
#             return account
#
#         product = self.product_id
#         if not product:
#             return account
#
#         categ = product.categ_id
#
#         # Handle Odoo 19 JSONB format: {"1": "real_time"}
#         val = categ.property_valuation
#         if isinstance(val, dict):
#             val_str = list(val.values())[0] if val else ''
#         else:
#             val_str = str(val) if val else ''
#
#         if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
#             return account
#
#         valuation_account = getattr(
#             categ, 'property_stock_valuation_account_id', False)
#         output_account = getattr(
#             categ, 'property_stock_account_output_categ_id', False)
#
#         # Replace stock valuation account with stock output account
#         if output_account and valuation_account \
#                 and account and account.id == valuation_account.id:
#             _logger.info(
#                 "Anglo-Saxon invoice fix: '%s' replacing %s -> %s",
#                 product.name,
#                 valuation_account.name,
#                 output_account.name
#             )
#             return output_account
#
#         return account
# -*- coding: utf-8 -*-
"""
account_move.py [v9 — FINAL]

Root cause of the bug:
======================
Image 2 shows the category "Accessories" has:
  Inventory Valuation = "Perpetual (at invoicing)"
  → Odoo 19 stores this as property_valuation = "perpetual_invoicing"

The previous version checked for:
  ('real_time', 'perpetual', 'perpetual_invoicing')  ← perpetual_invoicing WAS listed

BUT the real problem was that POS invoices are NOT created through
account.move.line._get_computed_account() at all.

In Odoo 19, POS invoice lines are created via:
  pos.order._generate_pos_order_invoice()
    → pos.order._prepare_invoice_line()
        → This calls product.product._get_product_accounts()
          and picks 'stock_output' key.

BUT in Odoo 19 CE without account_anglo_saxon, the standard
account.move._get_stock_valuation_account() is called instead,
which ignores 'stock_output' entirely and returns stock valuation.

THE TWO FIXES HERE:
1. ProductTemplate.get_product_accounts() — injects stock_output
   (already in v8, kept here)

2. pos.order._prepare_invoice_line() — directly replaces the account
   on POS invoice lines AFTER they are built
   (THIS is the fix that was missing)

3. AccountMoveLine._get_computed_account() — belt-and-suspenders for
   regular SO invoices.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)

# Valuation types that require Anglo-Saxon account substitution
PERPETUAL_TYPES = frozenset({'real_time', 'perpetual', 'perpetual_invoicing'})


def _get_valuation_str(categ):
    """Extract valuation string from category, handling Odoo 19 JSONB dict."""
    val = categ.property_valuation
    if not val:
        return ''
    if isinstance(val, dict):
        return list(val.values())[0] if val else ''
    return str(val)


def _get_output_account(categ):
    """Return (valuation_account, output_account) from category custom fields."""
    val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
    out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)
    return val_acct, out_acct


# ════════════════════════════════════════════════════════════════════
# FIX 1: get_product_accounts — used by standard SO invoice flow
# ════════════════════════════════════════════════════════════════════
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)

        categ = self.categ_id
        output_account = getattr(
            categ, 'property_stock_account_output_categ_id', False)
        valuation_account = getattr(
            categ, 'property_stock_valuation_account_id', False)
        input_account = getattr(
            categ, 'property_stock_account_input_categ_id', False)

        if output_account:
            accounts['stock_output'] = output_account
        if valuation_account:
            accounts['stock_valuation'] = valuation_account
        if input_account:
            accounts['stock_input'] = input_account

        _logger.debug(
            "get_product_accounts '%s': stock_output=%s stock_valuation=%s",
            self.name,
            output_account.name if output_account else 'None',
            valuation_account.name if valuation_account else 'None',
        )
        return accounts


# ════════════════════════════════════════════════════════════════════
# FIX 2: POS invoice line — THE CRITICAL FIX for POS orders
# ════════════════════════════════════════════════════════════════════
class PosOrderAccountFix(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_line(self, order_line):
        """
        POS INVOICE FIX: After Odoo builds the invoice line vals,
        replace 110100 Stock Valuation with 121200 Stock Interim (Deliverd).

        This is the ONLY reliable hook for POS invoice line accounts.
        _get_computed_account() is NOT called for POS invoice lines in Odoo 19.
        """
        vals = super()._prepare_invoice_line(order_line)

        product = order_line.product_id
        if not product:
            return vals

        categ = product.categ_id

        # Check valuation type
        val_str = _get_valuation_str(categ)
        if val_str not in PERPETUAL_TYPES:
            _logger.debug(
                "POS Invoice Fix: skipping '%s' (valuation=%s)",
                product.name, val_str)
            return vals

        val_acct, out_acct = _get_output_account(categ)

        if not val_acct or not out_acct:
            _logger.warning(
                "POS Invoice Fix: category '%s' missing accounts "
                "(val_acct=%s, out_acct=%s). Skipping.",
                categ.name,
                val_acct.name if val_acct else 'NOT SET',
                out_acct.name if out_acct else 'NOT SET',
            )
            return vals

        if val_acct.id == out_acct.id:
            _logger.warning(
                "POS Invoice Fix: valuation and output account are SAME "
                "(%s) on category '%s'. Check configuration.",
                val_acct.name, categ.name)
            return vals

        current_account_id = vals.get('account_id')

        if current_account_id == val_acct.id:
            vals['account_id'] = out_acct.id
            _logger.info(
                "POS Invoice Fix ✓ product='%s' category='%s' "
                "valuation='%s' replaced account %s (%s) → %s (%s)",
                product.name,
                categ.name,
                val_str,
                val_acct.code, val_acct.name,
                out_acct.code, out_acct.name,
            )
        else:
            _logger.debug(
                "POS Invoice Fix: product='%s' account_id=%s is NOT "
                "val_acct %s — no replacement needed.",
                product.name, current_account_id, val_acct.id)

        return vals


# ════════════════════════════════════════════════════════════════════
# FIX 3: AccountMoveLine hook — safety net for SO invoice flow
# ════════════════════════════════════════════════════════════════════
class AccountMoveLineFix(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_account(self):
        account = super()._get_computed_account()

        move = self.move_id
        if move.move_type not in ('out_invoice', 'out_refund'):
            return account

        product = self.product_id
        if not product or not account:
            return account

        categ = product.categ_id
        val_str = _get_valuation_str(categ)

        if val_str not in PERPETUAL_TYPES:
            return account

        val_acct, out_acct = _get_output_account(categ)

        if out_acct and val_acct and account.id == val_acct.id:
            _logger.info(
                "AccountMoveLine Fix ✓ product='%s' replacing %s → %s",
                product.name, val_acct.name, out_acct.name,
            )
            return out_acct

        return account