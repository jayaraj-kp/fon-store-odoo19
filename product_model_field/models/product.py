# from odoo import models, fields, api, _
# from odoo.exceptions import ValidationError
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     model_number = fields.Char(
#         string='Model',
#         size=255,
#         tracking=True,
#         help='Alphanumeric model number/identifier for the product'
#     )
#
#     mrp_price = fields.Float(
#         string='MRP Price',
#         digits='Product Price',
#         tracking=True,
#         help='Maximum Retail Price (MRP) of the product'
#     )
#
#     @api.constrains('list_price', 'mrp_price')
#     def _check_sale_price_vs_mrp(self):
#         for product in self:
#             if product.mrp_price > 0 and product.list_price > product.mrp_price:
#                 raise ValidationError(_(
#                     '⚠️ Sales Price Cannot Exceed MRP Price!\n\n'
#                     'Product  : %s\n'
#                     'Sales Price : ₹ %.2f\n'
#                     'MRP Price   : ₹ %.2f\n\n'
#                     'Please set the Sales Price equal to or less than the MRP Price.'
#                 ) % (product.name, product.list_price, product.mrp_price))
#
#
# class ProductProduct(models.Model):
#     _inherit = 'product.product'
#
#     model_number = fields.Char(
#         string='Model',
#         size=255,
#         tracking=True,
#         help='Alphanumeric model number/identifier for the product'
#     )
#
#     mrp_price = fields.Float(
#         string='MRP Price',
#         digits='Product Price',
#         tracking=True,
#         help='Maximum Retail Price (MRP) of the product'
#     )
#
#     @api.constrains('lst_price', 'mrp_price')
#     def _check_sale_price_vs_mrp(self):
#         for product in self:
#             if product.mrp_price > 0 and product.lst_price > product.mrp_price:
#                 raise ValidationError(_(
#                     '⚠️ Sales Price Cannot Exceed MRP Price!\n\n'
#                     'Product  : %s\n'
#                     'Sales Price : ₹ %.2f\n'
#                     'MRP Price   : ₹ %.2f\n\n'
#                     'Please set the Sales Price equal to or less than the MRP Price.'
#                 ) % (product.name, product.lst_price, product.mrp_price))
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    model_number = fields.Char(
        string='Model',
        size=255,
        tracking=True,
        help='Alphanumeric model number/identifier for the product'
    )

    mrp_price = fields.Float(
        string='MRP Price',
        digits='Product Price',
        tracking=True,
        help='Maximum Retail Price (MRP) of the product'
    )

    @api.constrains('list_price', 'mrp_price')
    def _check_sale_price_vs_mrp(self):
        for product in self:
            if product.mrp_price > 0 and product.list_price > product.mrp_price:
                raise ValidationError(_(
                    '⚠️ Sales Price Cannot Exceed MRP Price!\n\n'
                    'Product  : %s\n'
                    'Sales Price : ₹ %.2f\n'
                    'MRP Price   : ₹ %.2f\n\n'
                    'Please set the Sales Price equal to or less than the MRP Price.'
                ) % (product.name, product.list_price, product.mrp_price))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    model_number = fields.Char(
        string='Model',
        size=255,
        tracking=True,
        help='Alphanumeric model number/identifier for the product'
    )

    mrp_price = fields.Float(
        string='MRP Price',
        digits='Product Price',
        tracking=True,
        help='Maximum Retail Price (MRP) of the product'
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields = super()._load_pos_data_fields(config)
        if 'mrp_price' not in fields:
            fields.append('mrp_price')
        return fields

    @api.constrains('lst_price', 'mrp_price')
    def _check_sale_price_vs_mrp(self):
        for product in self:
            if product.mrp_price > 0 and product.lst_price > product.mrp_price:
                raise ValidationError(_(
                    '⚠️ Sales Price Cannot Exceed MRP Price!\n\n'
                    'Product  : %s\n'
                    'Sales Price : ₹ %.2f\n'
                    'MRP Price   : ₹ %.2f\n\n'
                    'Please set the Sales Price equal to or less than the MRP Price.'
                ) % (product.name, product.lst_price, product.mrp_price))