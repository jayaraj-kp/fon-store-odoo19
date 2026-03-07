# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """
    Extends product.template with two extra barcode + package-quantity pairs.

    Use-case example:
        Product : Eggs
        Barcode         (standard)  → qty  1  (single egg or 1 unit)
        Barcode 2  + Package Qty 1  → qty 12  (scan dozen barcode → 12 units)
        Barcode 3  + Package Qty 2  → qty 120 (scan bulk pack barcode → 120 units)

    The POS JS layer reads these fields and automatically applies the correct
    quantity (and therefore the correct total price = unit_price × qty) whenever
    Barcode 2 or Barcode 3 is scanned.
    """

    _inherit = 'product.template'

    # ── Barcode 2 ──────────────────────────────────────────────────────────────
    barcode2 = fields.Char(
        string='Barcode 2',
        copy=False,
        index=True,
        help='Secondary barcode — typically for a mid-size package '
             '(e.g. 1 dozen). Scanning this in POS will add Package Qty 1 '
             'of this product to the order.',
    )
    custom_qty1 = fields.Float(
        string='Package Qty 1',
        digits='Product Unit of Measure',
        default=1.0,
        help='Quantity to add when Barcode 2 is scanned '
             '(e.g. 12 for "1 dozen").',
    )

    # ── Barcode 3 ──────────────────────────────────────────────────────────────
    barcode3 = fields.Char(
        string='Barcode 3',
        copy=False,
        index=True,
        help='Third barcode — typically for a large/bulk package '
             '(e.g. 10 dozen). Scanning this in POS will add Package Qty 2 '
             'of this product to the order.',
    )
    custom_qty2 = fields.Float(
        string='Package Qty 2',
        digits='Product Unit of Measure',
        default=1.0,
        help='Quantity to add when Barcode 3 is scanned '
             '(e.g. 120 for "10 dozen").',
    )

    # ── SQL Constraints (DB-level, no ORM cascade, no default_code side effects)
    _sql_constraints = [
        (
            'barcode2_unique',
            'UNIQUE(barcode2)',
            'Barcode 2 must be unique across all products.',
        ),
        (
            'barcode3_unique',
            'UNIQUE(barcode3)',
            'Barcode 3 must be unique across all products.',
        ),
    ]

    # ── Python constraint  (only checks fields on THIS record — no search())  ──
    @api.constrains('barcode', 'barcode2', 'barcode3')
    def _check_barcodes_distinct_on_same_product(self):
        """
        Ensures the three barcodes on the SAME product are all different.
        No self.search() is used here so no cascade validation is triggered.
        Global uniqueness is already enforced by the SQL UNIQUE constraints above.
        """
        for rec in self:
            active = [b for b in (rec.barcode, rec.barcode2, rec.barcode3) if b]
            if len(active) != len(set(active)):
                raise ValidationError(
                    _(
                        'Barcode, Barcode 2 and Barcode 3 on the same product '
                        'must all be different. Please check product "%s".'
                    ) % rec.display_name
                )

    # ── Helper ─────────────────────────────────────────────────────────────────

    @api.model
    def search_by_any_barcode(self, barcode):
        """
        Returns (product_template, quantity) for any of the three barcode fields.
        Useful for server-side barcode lookups (e.g. from a custom wizard).
        Returns (record, qty) or (empty_record, 1).
        """
        product = self.search([('barcode', '=', barcode)], limit=1)
        if product:
            return product, 1.0

        product = self.search([('barcode2', '=', barcode)], limit=1)
        if product:
            return product, product.custom_qty1

        product = self.search([('barcode3', '=', barcode)], limit=1)
        if product:
            return product, product.custom_qty2

        return self.browse(), 1.0
