# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrder(models.Model):
    """
    Inherit Purchase Order model to make the Order Reference field optional.
    This allows importing purchase orders without requiring a value in the name field.
    """
    _inherit = 'purchase.order'

    # Override the name field to make it optional (not required)
    name = fields.Char(
        string='Order Reference',
        required=False,
        default='/',
        copy=False,
        readonly=False,
        tracking=True,
        help='The purchase order reference number. This field is optional.'
    )


class PurchaseOrderLine(models.Model):
    """
    Inherit Purchase Order Line model to make the name field optional.
    This allows importing purchase order lines without requiring a product name/description.
    """
    _inherit = 'purchase.order.line'

    # Override the name field to make it optional (not required)
    name = fields.Text(
        string='Description',
        required=False,
        help='Product description. This field is optional during import.'
    )
