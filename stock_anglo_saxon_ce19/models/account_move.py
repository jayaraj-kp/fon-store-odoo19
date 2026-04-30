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
account_move.py [v9]

Fixes customer invoice COGS line to use Stock Output / Interim Delivered (121200)
instead of Stock Valuation (110100).

ROOT CAUSE (Odoo 19 CE, POS flow):
  Odoo 19 creates the COGS line via stock_account's _stock_account_anglo_saxon_*
  methods. Without account_anglo_saxon installed, it resolves the credit account
  from `product.categ_id.property_account_expense_categ_id`, which in turn falls
  back to the stock valuation account (110100).

  Our _get_computed_account() override DOES fire for normal invoices, but for
  POS auto-invoices Odoo bypasses it and writes the line directly.

SOLUTION — THREE-LAYER APPROACH:
  1. get_product_accounts() override on product.template
       → Injects correct stock_output/input/valuation from our custom fields
         for any code path that calls this method.

  2. _get_computed_account() override on account.move.line
       → Catches any remaining valuation→output mismatches for out_invoice/refund.

  3. _post() override on account.move
       → Final safety net: after the move is posted, scan all lines
         and replace any lingering 110100 (stock valuation) credits
         with 121200 (stock output) on customer invoices.
         Uses sudo() + check_move_validity=False to rewrite posted lines.

All three layers read accounts exclusively from our custom category fields:
  - property_stock_valuation_account_id      (110100 Stock Valuation)
  - property_stock_account_output_categ_id   (121200 Stock Interim Delivered)
  - property_stock_account_input_categ_id    (230300 Stock Interim Received)
"""
import logging
from odoo import models, api, _

_logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════
# LAYER 1 — product.template.get_product_accounts()
# Inject correct accounts for any code path that calls this.
# ════════════════════════════════════════════════════════════════════

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        """
        Inject stock_output / stock_valuation / stock_input from our
        custom product category fields into the accounts dict.
        """
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)

        categ = self.categ_id
        output_account    = getattr(categ, 'property_stock_account_output_categ_id', False)
        valuation_account = getattr(categ, 'property_stock_valuation_account_id',   False)
        input_account     = getattr(categ, 'property_stock_account_input_categ_id',  False)

        if output_account:
            accounts['stock_output'] = output_account
            _logger.debug(
                "Anglo-Saxon v9 [get_product_accounts] '%s': stock_output → %s",
                self.name, output_account.code)

        if valuation_account:
            accounts['stock_valuation'] = valuation_account
            _logger.debug(
                "Anglo-Saxon v9 [get_product_accounts] '%s': stock_valuation → %s",
                self.name, valuation_account.code)

        if input_account:
            accounts['stock_input'] = input_account
            _logger.debug(
                "Anglo-Saxon v9 [get_product_accounts] '%s': stock_input → %s",
                self.name, input_account.code)

        return accounts


# ════════════════════════════════════════════════════════════════════
# LAYER 2 — account.move.line._get_computed_account()
# Intercept during line construction (normal invoice flow).
# ════════════════════════════════════════════════════════════════════

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_account(self):
        """
        For customer invoices/refunds: replace Stock Valuation (110100)
        with Stock Output / Interim Delivered (121200) on COGS lines.
        """
        account = super()._get_computed_account()

        move = self.move_id
        if move.move_type not in ('out_invoice', 'out_refund'):
            return account

        product = self.product_id
        if not product:
            return account

        categ = product.categ_id
        if not self._anglo_saxon_is_perpetual(categ):
            return account

        valuation_account = getattr(categ, 'property_stock_valuation_account_id',   False)
        output_account    = getattr(categ, 'property_stock_account_output_categ_id', False)

        if output_account and valuation_account \
                and account and account.id == valuation_account.id:
            _logger.info(
                "Anglo-Saxon v9 [_get_computed_account] '%s': %s → %s",
                product.name, valuation_account.code, output_account.code)
            return output_account

        return account

    # ── helper ──────────────────────────────────────────────────────
    @staticmethod
    def _anglo_saxon_is_perpetual(categ):
        """True if the category uses real-time (perpetual) valuation.
        Handles both plain string and Odoo 19 JSONB dict formats."""
        val = categ.property_valuation
        if not val:
            return False
        if isinstance(val, dict):
            val_str = list(val.values())[0] if val else ''
        else:
            val_str = str(val)
        return val_str in ('real_time', 'perpetual', 'perpetual_invoicing')


# ════════════════════════════════════════════════════════════════════
# LAYER 3 — account.move._post()
# Final safety-net: fix any already-written lines before/after posting.
# This catches POS auto-invoice lines that bypass _get_computed_account.
# ════════════════════════════════════════════════════════════════════

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        """
        Before posting: scan customer invoice lines and replace any
        Stock Valuation credit with Stock Output (Interim Delivered).
        Uses sudo() + context flags to bypass move-lock restrictions.
        """
        for move in self.filtered(
                lambda m: m.move_type in ('out_invoice', 'out_refund')):
            self._fix_anglo_saxon_output_account(move)

        return super()._post(soft=soft)

    # ── helper called by _post ───────────────────────────────────────
    @api.model
    def _fix_anglo_saxon_output_account(self, move):
        """
        Scan all lines of a customer invoice.
        For any line whose account = Stock Valuation (110100) and whose
        product belongs to a perpetual-valuation category, replace that
        account with the Stock Output / Interim Delivered account (121200).
        """
        lines_fixed = 0
        for line in move.line_ids:
            product = line.product_id
            if not product:
                continue

            categ = product.categ_id
            if not AccountMoveLine._anglo_saxon_is_perpetual(categ):
                continue

            valuation_account = getattr(
                categ, 'property_stock_valuation_account_id', False)
            output_account    = getattr(
                categ, 'property_stock_account_output_categ_id', False)

            if not valuation_account or not output_account:
                continue

            if line.account_id and line.account_id.id == valuation_account.id:
                try:
                    line.sudo().with_context(
                        check_move_validity=False,
                        skip_account_move_synchronization=True,
                    ).account_id = output_account.id
                    lines_fixed += 1
                    _logger.info(
                        "Anglo-Saxon v9 [_post fix] move=%s line=%s "
                        "product='%s': %s → %s",
                        move.name, line.id, product.name,
                        valuation_account.code, output_account.code,
                    )
                except Exception as e:
                    _logger.warning(
                        "Anglo-Saxon v9 [_post fix] Could not fix line %s "
                        "on move %s: %s", line.id, move.name, e)

        if lines_fixed:
            _logger.info(
                "Anglo-Saxon v9 [_post fix] Fixed %d line(s) on move '%s'",
                lines_fixed, move.name)