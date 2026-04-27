# # -*- coding: utf-8 -*-
# from odoo import models, api
#
#
# class ProductCategory(models.Model):
#     """
#     Overrides default_get for product.category.
#     In Odoo 19 the costing method field is 'property_cost_method'
#     with selection key 'average' for AVCO.
#     Property fields ARE included in fields_list, but their default
#     is set via ir.property — we force override after super().
#     """
#     _inherit = 'product.category'
#
#     @api.model
#     def default_get(self, fields_list):
#         defaults = super().default_get(fields_list)
#         # 'property_cost_method' is the real field; selection key is 'average'
#         # We always overwrite whatever the parent/ir.property set
#         defaults['property_cost_method'] = 'average'
#         return defaults

# -*- coding: utf-8 -*-
from odoo import models, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        # --- Costing Method: AVCO ---
        defaults['property_cost_method'] = 'average'

        # --- Inventory Valuation: Perpetual (at invoicing) ---
        defaults['property_valuation'] = 'real_time'

        company = self.env.company

        # --- Stock Valuation Account (search by account code) ---
        valuation_account = self.env['account.account'].search([
            ('code', '=', '360000'),          # Change to your actual account code
            ('company_id', '=', company.id),
        ], limit=1)
        if valuation_account:
            defaults['property_stock_valuation_account_id'] = valuation_account.id

        # --- Stock Journal (search by journal name) ---
        stock_journal = self.env['account.journal'].search([
            ('name', 'ilike', 'Inventory Valuation'),  # Change to your actual journal name
            ('company_id', '=', company.id),
        ], limit=1)
        if stock_journal:
            defaults['stock_journal_id'] = stock_journal.id

        return defaults