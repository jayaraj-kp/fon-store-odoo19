# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """
        Override fields_get to mark restricted fields as non-readable
        for users who have the corresponding restriction enabled.
        """
        res = super().fields_get(allfields=allfields, attributes=attributes)
        user = self.env.user

        fields_to_check = {
            'standard_price': 'restrict_cost_price',
            'list_price': 'restrict_sales_price',
            'barcode': 'restrict_barcode',
            'default_code': 'restrict_internal_reference',
            'taxes_id': 'restrict_taxes',
            'supplier_taxes_id': 'restrict_taxes',
        }

        for field_name, restriction_attr in fields_to_check.items():
            if getattr(user, restriction_attr, False) and field_name in res:
                # Mark the field as invisible / no groups workaround
                res[field_name]['invisible'] = True

        return res

    def read(self, fields=None, load='_classic_read'):
        """
        Intercept read to blank out restricted field values for the current user.
        """
        result = super().read(fields=fields, load=load)
        user = self.env.user

        restricted_map = {
            'standard_price': 'restrict_cost_price',
            'list_price': 'restrict_sales_price',
            'barcode': 'restrict_barcode',
            'default_code': 'restrict_internal_reference',
        }

        for record in result:
            for field_name, restriction_attr in restricted_map.items():
                if field_name in record and getattr(user, restriction_attr, False):
                    # Return False/empty instead of the real value
                    if isinstance(record[field_name], (int, float)):
                        record[field_name] = 0.0
                    else:
                        record[field_name] = False

        return result

    def write(self, vals):
        """Prevent writing to cost/price fields if user lacks permission."""
        user = self.env.user

        if 'standard_price' in vals and user.restrict_cost_price_edit:
            del vals['standard_price']

        if 'list_price' in vals and user.restrict_sales_price_edit:
            del vals['list_price']

        return super().write(vals)
