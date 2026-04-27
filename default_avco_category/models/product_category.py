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

        # --- Stock Journal: try multiple strategies ---
        stock_journal = None

        # Strategy 1: exact name match
        stock_journal = self.env['account.journal'].search([
            ('name', '=', 'Inventory Valuation'),
            ('company_id', '=', company.id),
        ], limit=1)

        # Strategy 2: partial name match
        if not stock_journal:
            stock_journal = self.env['account.journal'].search([
                ('name', 'ilike', 'Inventory'),
                ('company_id', '=', company.id),
            ], limit=1)

        # Strategy 3: fallback — any 'general' type journal
        if not stock_journal:
            stock_journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', company.id),
            ], limit=1)

        if stock_journal:
            defaults['stock_journal_id'] = stock_journal.id
            _logger.info("Default stock journal set to: %s (id=%s)", stock_journal.name, stock_journal.id)
        else:
            _logger.warning("No stock journal found for company %s", company.name)

        return defaults