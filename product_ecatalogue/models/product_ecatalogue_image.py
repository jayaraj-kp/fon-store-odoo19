# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductECatalogueImage(models.Model):
    _name = 'product.ecatalogue.image'
    _description = 'Product E-Catalogue Image'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Used to order images in the catalogue gallery.',
    )
    name = fields.Char(string='Image Name')
    image = fields.Image(
        string='Image',
        required=True,
        max_width=1920,
        max_height=1920,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        ondelete='cascade',
        index=True,
    )
