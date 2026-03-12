# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── Package 1 ─────────────────────────────────────────────────────────────
    barcode2 = fields.Char(
        string='Barcode 2', copy=False, index=True,
        help='Scan this barcode in POS to add Package Qty 1 at Package Price 1.',
    )
    custom_qty1 = fields.Float(
        string='Package Qty 1', digits='Product Unit of Measure', default=1.0,
        help='Quantity added when Barcode 2 is scanned (e.g. 12 for 1 dozen).',
    )
    custom_price1 = fields.Float(
        string='Package Price 1', digits='Product Price', default=0.0,
        help='Selling price for this package. Leave 0 to use unit price.',
    )
    max_combo_qty1 = fields.Integer(
        string='Max Combo Limit 1',
        default=5,
        help='Maximum number of times Package 1 (Barcode 2) can be scanned in a '
             'single POS bill. Set 0 for unlimited.',
    )

    # ── Package 2 ─────────────────────────────────────────────────────────────
    barcode3 = fields.Char(
        string='Barcode 3', copy=False, index=True,
        help='Scan this barcode in POS to add Package Qty 2 at Package Price 2.',
    )
    custom_qty2 = fields.Float(
        string='Package Qty 2', digits='Product Unit of Measure', default=1.0,
        help='Quantity added when Barcode 3 is scanned (e.g. 120 for 10 dozen).',
    )
    custom_price2 = fields.Float(
        string='Package Price 2', digits='Product Price', default=0.0,
        help='Selling price for this package. Leave 0 to use unit price.',
    )
    max_combo_qty2 = fields.Integer(
        string='Max Combo Limit 2',
        default=5,
        help='Maximum number of times Package 2 (Barcode 3) can be scanned in a '
             'single POS bill. Set 0 for unlimited.',
    )

    # ── SQL constraints ────────────────────────────────────────────────────────
    _sql_constraints = [
        ('barcode2_unique', 'UNIQUE(barcode2)', 'Barcode 2 must be unique across all products.'),
        ('barcode3_unique', 'UNIQUE(barcode3)', 'Barcode 3 must be unique across all products.'),
    ]

    @api.constrains('barcode', 'barcode2', 'barcode3')
    def _check_barcodes_distinct_on_same_product(self):
        for rec in self:
            active = [b for b in (rec.barcode, rec.barcode2, rec.barcode3) if b]
            if len(active) != len(set(active)):
                raise ValidationError(
                    _('Barcode, Barcode 2 and Barcode 3 on the same product '
                      'must all be different. Please check product "%s".') % rec.display_name
                )
