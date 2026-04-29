# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # ─── PRODUCT / COST RESTRICTIONS ────────────────────────────────────────────

    restrict_cost_price = fields.Boolean(
        string='Hide Cost Price',
        help='If enabled, this user cannot see the cost price of products.'
    )
    restrict_cost_price_edit = fields.Boolean(
        string='Restrict Cost Price Edit',
        help='If enabled, this user cannot edit the cost price of products.'
    )
    restrict_sales_price = fields.Boolean(
        string='Hide Sales Price',
        help='If enabled, this user cannot see the sales price of products.'
    )
    restrict_sales_price_edit = fields.Boolean(
        string='Restrict Sales Price Edit',
        help='If enabled, this user cannot edit the sales price of products.'
    )
    restrict_barcode = fields.Boolean(
        string='Hide Barcode',
        help='If enabled, this user cannot see the barcode field on products.'
    )
    restrict_internal_reference = fields.Boolean(
        string='Hide Internal Reference',
        help='If enabled, this user cannot see the internal reference on products.'
    )
    restrict_taxes = fields.Boolean(
        string='Hide Tax Fields',
        help='If enabled, this user cannot see the tax fields on products.'
    )
    restrict_product_margin = fields.Boolean(
        string='Hide Product Margin',
        help='If enabled, this user cannot see product margin information.'
    )

    # ─── ACCOUNTING REPORTS RESTRICTIONS ────────────────────────────────────────

    restrict_balance_sheet = fields.Boolean(
        string='Hide Balance Sheet',
        help='If enabled, this user cannot access the Balance Sheet report.'
    )
    restrict_profit_loss = fields.Boolean(
        string='Hide Profit & Loss',
        help='If enabled, this user cannot access the Profit & Loss report.'
    )
    restrict_partner_ledger = fields.Boolean(
        string='Hide Partner Ledger',
        help='If enabled, this user cannot access the Partner Ledger report.'
    )
    restrict_general_ledger = fields.Boolean(
        string='Hide General Ledger',
        help='If enabled, this user cannot access the General Ledger report.'
    )
    restrict_trial_balance = fields.Boolean(
        string='Hide Trial Balance',
        help='If enabled, this user cannot access the Trial Balance report.'
    )
    restrict_cash_flow = fields.Boolean(
        string='Hide Cash Flow Statement',
        help='If enabled, this user cannot access the Cash Flow Statement report.'
    )
    restrict_aged_receivable = fields.Boolean(
        string='Hide Aged Receivable',
        help='If enabled, this user cannot access the Aged Receivable report.'
    )
    restrict_aged_payable = fields.Boolean(
        string='Hide Aged Payable',
        help='If enabled, this user cannot access the Aged Payable report.'
    )
    restrict_tax_report = fields.Boolean(
        string='Hide Tax Report',
        help='If enabled, this user cannot access the Tax Report.'
    )
    restrict_executive_summary = fields.Boolean(
        string='Hide Executive Summary',
        help='If enabled, this user cannot access the Executive Summary report.'
    )

    # ─── INVENTORY RESTRICTIONS ──────────────────────────────────────────────────

    restrict_scrap_menu = fields.Boolean(
        string='Hide Scrap Menu',
        help='If enabled, this user cannot see or access the Scrap menu in Inventory.'
    )
    restrict_physical_inventory = fields.Boolean(
        string='Hide Physical Inventory Adjustment',
        help='If enabled, this user cannot access the Physical Inventory Adjustment.'
    )
    restrict_inventory_valuation = fields.Boolean(
        string='Hide Inventory Valuation',
        help='If enabled, this user cannot access the Inventory Valuation report.'
    )
    restrict_replenishment = fields.Boolean(
        string='Hide Replenishment Menu',
        help='If enabled, this user cannot see the Replenishment menu.'
    )
    restrict_landed_costs = fields.Boolean(
        string='Hide Landed Costs',
        help='If enabled, this user cannot access Landed Costs.'
    )

    # ─── HELPERS: expose restrictions as a dict for RPC use ─────────────────────

    @api.model
    def get_current_user_restrictions(self):
        """Return the restriction flags for the currently logged-in user."""
        user = self.env.user
        return {
            # product
            'restrict_cost_price': user.restrict_cost_price,
            'restrict_cost_price_edit': user.restrict_cost_price_edit,
            'restrict_sales_price': user.restrict_sales_price,
            'restrict_sales_price_edit': user.restrict_sales_price_edit,
            'restrict_barcode': user.restrict_barcode,
            'restrict_internal_reference': user.restrict_internal_reference,
            'restrict_taxes': user.restrict_taxes,
            'restrict_product_margin': user.restrict_product_margin,
            # reports
            'restrict_balance_sheet': user.restrict_balance_sheet,
            'restrict_profit_loss': user.restrict_profit_loss,
            'restrict_partner_ledger': user.restrict_partner_ledger,
            'restrict_general_ledger': user.restrict_general_ledger,
            'restrict_trial_balance': user.restrict_trial_balance,
            'restrict_cash_flow': user.restrict_cash_flow,
            'restrict_aged_receivable': user.restrict_aged_receivable,
            'restrict_aged_payable': user.restrict_aged_payable,
            'restrict_tax_report': user.restrict_tax_report,
            'restrict_executive_summary': user.restrict_executive_summary,
            # inventory
            'restrict_scrap_menu': user.restrict_scrap_menu,
            'restrict_physical_inventory': user.restrict_physical_inventory,
            'restrict_inventory_valuation': user.restrict_inventory_valuation,
            'restrict_replenishment': user.restrict_replenishment,
            'restrict_landed_costs': user.restrict_landed_costs,
        }
