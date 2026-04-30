# # -*- coding: utf-8 -*-
# """
# account_move.py [v7]
#
# Fixes the customer invoice COGS entry to use the correct
# Stock Output Account (121200 Stock Interim Delivered)
# instead of Stock Valuation (110100).
#
# When Odoo 19 confirms a customer invoice, it creates:
#     DR  600000 Expenses (COGS)
#     CR  ??? Stock account
#
# It reads the stock account from product_tmpl_id.get_product_accounts()
# which looks for 'stock_output' key. In Odoo 19 CE without account_anglo_saxon,
# this falls back to the stock valuation account.
#
# This module overrides get_product_accounts() on product.template to
# inject the correct output account from our custom category field.
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
#                 "Anglo-Saxon v7: get_product_accounts '%s' "
#                 "stock_output => %s", self.name, output_account.name)
#
#         if valuation_account:
#             accounts['stock_valuation'] = valuation_account
#             _logger.debug(
#                 "Anglo-Saxon v7: get_product_accounts '%s' "
#                 "stock_valuation => %s", self.name, valuation_account.name)
#
#         if input_account:
#             accounts['stock_input'] = input_account
#             _logger.debug(
#                 "Anglo-Saxon v7: get_product_accounts '%s' "
#                 "stock_input => %s", self.name, input_account.name)
#
#         return accounts
#
#
# # At bottom of account_move.py, add this new class:
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     def _get_computed_account(self):
#         """
#         Odoo 19 CE: Override to use stock_output account (121200)
#         instead of stock_valuation (110100) for COGS lines on invoices.
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
#         val = categ.property_valuation
#
#         # Check if perpetual valuation (handle JSONB dict)
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
#         # If current account is stock valuation, replace with stock output
#         if output_account and valuation_account \
#                 and account == valuation_account:
#             _logger.info(
#                 "Anglo-Saxon invoice fix: replacing %s with %s for '%s'",
#                 valuation_account.name, output_account.name, product.name
#             )
#             return output_account
#
#         return account
#
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
#                 "Anglo-Saxon invoice fix: '%s' replacing %s → %s",
#                 product.name,
#                 valuation_account.name,
#                 output_account.name
#             )
#             return output_account
#
#         return account
# -*- coding: utf-8 -*-
"""
account_move.py [v8]

Fixes the customer invoice COGS entry to use the correct
Stock Output Account (121200 Stock Interim Delivered)
instead of Stock Valuation (110100).
"""
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def get_product_accounts(self, fiscal_pos=None):
        """
        Override to inject the correct stock output account
        from our custom field property_stock_account_output_categ_id.
        """
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
            _logger.debug(
                "Anglo-Saxon v8: get_product_accounts '%s' "
                "stock_output => %s", self.name, output_account.name)

        if valuation_account:
            accounts['stock_valuation'] = valuation_account
            _logger.debug(
                "Anglo-Saxon v8: get_product_accounts '%s' "
                "stock_valuation => %s", self.name, valuation_account.name)

        if input_account:
            accounts['stock_input'] = input_account
            _logger.debug(
                "Anglo-Saxon v8: get_product_accounts '%s' "
                "stock_input => %s", self.name, input_account.name)

        return accounts


# NOTE: Only ONE AccountMoveLine class — the previous version had a duplicate
# which caused the first definition to be silently overwritten by Python.
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_computed_account(self):
        """
        Odoo 19 CE: For customer invoices, replace Stock Valuation (110100)
        with Stock Output/Interim Delivered (121200) on COGS lines.
        """
        account = super()._get_computed_account()

        move = self.move_id
        if move.move_type not in ('out_invoice', 'out_refund'):
            return account

        product = self.product_id
        if not product:
            return account

        categ = product.categ_id

        # Handle Odoo 19 JSONB format: {"1": "real_time"}
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

        # Replace stock valuation account with stock output account
        if output_account and valuation_account \
                and account and account.id == valuation_account.id:
            _logger.info(
                "Anglo-Saxon invoice fix: '%s' replacing %s -> %s",
                product.name,
                valuation_account.name,
                output_account.name
            )
            return output_account

        return account