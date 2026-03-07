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

    # ── Constraints ────────────────────────────────────────────────────────────

    @api.constrains('barcode', 'barcode2', 'barcode3')
    def _check_barcode_uniqueness(self):
        """
        Ensures:
          1. barcode, barcode2, barcode3 are mutually distinct on the same product.
          2. barcode2 / barcode3 are globally unique across all products.
        """
        for rec in self:
            active_barcodes = [b for b in [rec.barcode, rec.barcode2, rec.barcode3] if b]
            if len(active_barcodes) != len(set(active_barcodes)):
                raise ValidationError(
                    _('Barcode, Barcode 2 and Barcode 3 on the same product must all be different.')
                )

            if rec.barcode2:
                duplicate = self.search(
                    [('barcode2', '=', rec.barcode2), ('id', '!=', rec.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _('Barcode 2 "%s" is already used by product "%s".')
                        % (rec.barcode2, duplicate.display_name)
                    )
                # Also check it doesn't clash with any standard barcode
                clash = self.search(
                    [('barcode', '=', rec.barcode2), ('id', '!=', rec.id)],
                    limit=1,
                )
                if clash:
                    raise ValidationError(
                        _('Barcode 2 "%s" is already used as the main barcode of product "%s".')
                        % (rec.barcode2, clash.display_name)
                    )

            if rec.barcode3:
                duplicate = self.search(
                    [('barcode3', '=', rec.barcode3), ('id', '!=', rec.id)],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _('Barcode 3 "%s" is already used by product "%s".')
                        % (rec.barcode3, duplicate.display_name)
                    )
                clash = self.search(
                    [('barcode', '=', rec.barcode3), ('id', '!=', rec.id)],
                    limit=1,
                )
                if clash:
                    raise ValidationError(
                        _('Barcode 3 "%s" is already used as the main barcode of product "%s".')
                        % (rec.barcode3, clash.display_name)
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
