# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductProduct(models.Model):
    """
    Mirror the custom barcode / qty fields from product.template onto
    product.product as STORED related fields.

    Why this is needed
    ──────────────────
    Odoo POS loads product.product records (variants), not product.template.
    Although product.product inherits template fields via _inherits, the POS
    data-loader only sends fields that are explicitly declared on product.product
    (or listed in the loader params).  By adding stored related fields here we
    guarantee:

      1. The fields physically exist on product.product in the ORM sense.
      2. The POS _loader_params override can reference them by name.
      3. Even if the loader override fails (e.g. method renamed in a future
         Odoo version), the JS can still access the values because they are
         part of the default product.product field set once stored=True.
    """

    _inherit = 'product.product'

    barcode2 = fields.Char(
        related='product_tmpl_id.barcode2',
        string='Barcode 2',
        store=True,
        readonly=False,
        help='Package barcode 2 — mirrors the value on the product template.',
    )
    custom_qty1 = fields.Float(
        related='product_tmpl_id.custom_qty1',
        string='Package Qty 1',
        store=True,
        readonly=False,
        digits='Product Unit of Measure',
    )

    barcode3 = fields.Char(
        related='product_tmpl_id.barcode3',
        string='Barcode 3',
        store=True,
        readonly=False,
        help='Package barcode 3 — mirrors the value on the product template.',
    )
    custom_qty2 = fields.Float(
        related='product_tmpl_id.custom_qty2',
        string='Package Qty 2',
        store=True,
        readonly=False,
        digits='Product Unit of Measure',
    )
