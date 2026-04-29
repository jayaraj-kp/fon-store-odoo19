# -*- coding: utf-8 -*-
from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def read(self, fields=None, load='_classic_read'):
        """
        Blank out restricted field values for the current user at ORM level.
        This ensures the data is hidden even via API calls.
        """
        result = super().read(fields=fields, load=load)
        user = self.env.user

        if user._is_superuser():
            return result

        restricted_scalar = {
            'standard_price': 'restrict_cost_price',
            'list_price':     'restrict_sales_price',
            'barcode':        'restrict_barcode',
            'default_code':   'restrict_internal_reference',
        }
        restricted_m2m = {
            'taxes_id':          'restrict_taxes',
            'supplier_taxes_id': 'restrict_taxes',
        }

        for record in result:
            for field_name, attr in restricted_scalar.items():
                if field_name in record and getattr(user, attr, False):
                    val = record[field_name]
                    record[field_name] = 0.0 if isinstance(val, (int, float)) else False

            for field_name, attr in restricted_m2m.items():
                if field_name in record and getattr(user, attr, False):
                    record[field_name] = []   # empty list = no taxes shown

        return result

    def write(self, vals):
        """Block write on restricted fields."""
        user = self.env.user
        if not user._is_superuser():
            if 'standard_price' in vals and user.restrict_cost_price_edit:
                del vals['standard_price']
            if 'list_price' in vals and user.restrict_sales_price_edit:
                del vals['list_price']
        return super().write(vals)


class ProductProduct(models.Model):
    """Apply same restrictions to product.product (variant) reads."""
    _inherit = 'product.product'

    def read(self, fields=None, load='_classic_read'):
        result = super().read(fields=fields, load=load)
        user = self.env.user

        if user._is_superuser():
            return result

        restricted_scalar = {
            'standard_price': 'restrict_cost_price',
            'list_price':     'restrict_sales_price',
            'barcode':        'restrict_barcode',
            'default_code':   'restrict_internal_reference',
        }
        restricted_m2m = {
            'taxes_id':          'restrict_taxes',
            'supplier_taxes_id': 'restrict_taxes',
        }

        for record in result:
            for field_name, attr in restricted_scalar.items():
                if field_name in record and getattr(user, attr, False):
                    val = record[field_name]
                    record[field_name] = 0.0 if isinstance(val, (int, float)) else False
            for field_name, attr in restricted_m2m.items():
                if field_name in record and getattr(user, attr, False):
                    record[field_name] = []

        return result
