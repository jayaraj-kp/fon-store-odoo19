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
# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


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

        # --- Stock Valuation Account ---
        valuation_account = self.env['account.account'].search([
            ('code', '=', '360000'),
            ('company_ids', 'in', company.id),
        ], limit=1)
        if valuation_account:
            defaults['property_stock_valuation_account_id'] = valuation_account.id

        # --- Stock Journal (correct field name for Odoo 19) ---
        stock_journal = self.env['account.journal'].search([
            ('name', '=', 'Inventory Valuation'),
            ('company_id', '=', company.id),
        ], limit=1)
        if stock_journal:
            defaults['property_stock_journal'] = stock_journal.id
            _logger.info("Set property_stock_journal = %s (id=%s)", stock_journal.name, stock_journal.id)
        else:
            _logger.warning("Stock journal 'Inventory Valuation' not found for company %s", company.name)

        return defaults