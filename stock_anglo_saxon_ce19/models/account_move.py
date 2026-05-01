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
# -*- coding: utf-8 -*-
"""
account_move.py [v10 — FINAL CORRECT FIX]

ROOT CAUSE (confirmed from logs + chatter):
============================================
The invoice chatter says:
  "This invoice has been created from the point of sale session:
   FON-STORE KONDOTTY - 000034"

This means Odoo 19 creates POS invoices at SESSION CLOSING via
pos.session._create_account_move() — NOT via pos.order._prepare_invoice_line().

The session closing builds the invoice move directly using line_ids
with raw account IDs, bypassing both:
  - pos.order._prepare_invoice_line()   ← our previous fix target (WRONG)
  - account.move.line._get_computed_account()  ← only fires on onchange

THE CORRECT FIX:
================
Override account.move.line.create() to intercept ALL invoice line creation,
including session-based ones. This is the one method that ALWAYS fires
regardless of how the invoice is created.

We check: if a customer invoice line is being created with the stock
valuation account (110100), replace it with the stock output account (121200).
"""
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

PERPETUAL_TYPES = frozenset({'real_time', 'perpetual', 'perpetual_invoicing'})


def _get_valuation_str(categ):
    val = categ.property_valuation
    if not val:
        return ''
    if isinstance(val, dict):
        return list(val.values())[0] if val else ''
    return str(val)


# ════════════════════════════════════════════════════════════════════
# FIX 1: get_product_accounts — used by standard SO invoice flow
# ════════════════════════════════════════════════════════════════════
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
        categ = self.categ_id
        output_account = getattr(categ, 'property_stock_account_output_categ_id', False)
        valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
        input_account = getattr(categ, 'property_stock_account_input_categ_id', False)
        if output_account:
            accounts['stock_output'] = output_account
        if valuation_account:
            accounts['stock_valuation'] = valuation_account
        if input_account:
            accounts['stock_input'] = input_account
        return accounts


# ════════════════════════════════════════════════════════════════════
# FIX 2: Override account.move.line.create()
# This fires for ALL invoice line creation — session-based AND order-based
# ════════════════════════════════════════════════════════════════════
class AccountMoveLineFix(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Intercept invoice line creation and replace Stock Valuation account
        (110100) with Stock Interim Delivered account (121200) on customer
        invoice lines.

        This fires for ALL creation paths including pos.session closing.
        """
        for vals in vals_list:
            account_id = vals.get('account_id')
            product_id = vals.get('product_id')
            move_id = vals.get('move_id')

            if not account_id or not product_id or not move_id:
                continue

            move = self.env['account.move'].browse(move_id)
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue

            product = self.env['product.product'].browse(product_id)
            categ = product.categ_id

            val_str = _get_valuation_str(categ)
            if val_str not in PERPETUAL_TYPES:
                continue

            val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
            out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)

            if not val_acct or not out_acct or val_acct.id == out_acct.id:
                continue

            if account_id == val_acct.id:
                vals['account_id'] = out_acct.id
                _logger.info(
                    "AccountMoveLine.create Fix v10 ✓ move=%s product='%s' "
                    "category='%s' valuation='%s' "
                    "replaced %s (%s) -> %s (%s)",
                    move.name or move_id,
                    product.name,
                    categ.name,
                    val_str,
                    val_acct.code, val_acct.name,
                    out_acct.code, out_acct.name,
                )

        return super().create(vals_list)

    def _get_computed_account(self):
        """Belt-and-suspenders for onchange/draft invoice flows."""
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

        val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
        out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)

        if out_acct and val_acct and account.id == val_acct.id:
            _logger.info(
                "_get_computed_account Fix v10 ✓ product='%s' %s -> %s",
                product.name, val_acct.name, out_acct.name,
            )
            return out_acct

        return account