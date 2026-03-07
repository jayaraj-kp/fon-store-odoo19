# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── Barcode 2 & Package Qty 2 ─────────────────────────────────────────────
    barcode_2 = fields.Char(
        string='Barcode 2',
        help='Secondary barcode (e.g., for a dozen / small pack)',
        copy=False,
        index=True,
    )
    package_qty_2 = fields.Float(
        string='Package Qty 2',
        digits='Product Unit of Measure',
        default=0.0,
        help='Number of base units when this barcode is scanned. '
             'E.g. 12 for a dozen.',
    )
    package_name_2 = fields.Char(
        string='Package Label 2',
        help='Friendly label shown on POS / sale lines. E.g. "Dozen"',
    )

    # ── Barcode 3 & Package Qty 3 ─────────────────────────────────────────────
    barcode_3 = fields.Char(
        string='Barcode 3',
        help='Tertiary barcode (e.g., for a big carton / bulk pack)',
        copy=False,
        index=True,
    )
    package_qty_3 = fields.Float(
        string='Package Qty 3',
        digits='Product Unit of Measure',
        default=0.0,
        help='Number of base units when this barcode is scanned. '
             'E.g. 120 for 10 dozen.',
    )
    package_name_3 = fields.Char(
        string='Package Label 3',
        help='Friendly label shown on POS / sale lines. E.g. "Big Carton"',
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Constraints – barcodes must be unique across the whole product table
    # ──────────────────────────────────────────────────────────────────────────

    @api.constrains('barcode_2')
    def _check_barcode_2_unique(self):
        for rec in self:
            if not rec.barcode_2:
                continue
            # must not clash with barcode_2 on other templates
            dup = self.search([
                ('barcode_2', '=', rec.barcode_2),
                ('id', '!=', rec.id),
            ], limit=1)
            if dup:
                raise ValidationError(
                    _('Barcode 2 "%s" is already used by product "%s".')
                    % (rec.barcode_2, dup.display_name)
                )
            # must not clash with the main barcode field
            dup_main = self.search([
                ('barcode', '=', rec.barcode_2),
            ], limit=1)
            if dup_main:
                raise ValidationError(
                    _('Barcode 2 "%s" is already used as the main barcode '
                      'of product "%s".') % (rec.barcode_2, dup_main.display_name)
                )

    @api.constrains('barcode_3')
    def _check_barcode_3_unique(self):
        for rec in self:
            if not rec.barcode_3:
                continue
            dup = self.search([
                ('barcode_3', '=', rec.barcode_3),
                ('id', '!=', rec.id),
            ], limit=1)
            if dup:
                raise ValidationError(
                    _('Barcode 3 "%s" is already used by product "%s".')
                    % (rec.barcode_3, dup.display_name)
                )
            dup_main = self.search([
                ('barcode', '=', rec.barcode_3),
            ], limit=1)
            if dup_main:
                raise ValidationError(
                    _('Barcode 3 "%s" is already used as the main barcode '
                      'of product "%s".') % (rec.barcode_3, dup_main.display_name)
                )

    # ──────────────────────────────────────────────────────────────────────────
    # Helper – resolve any barcode to (product_variant, qty_multiplier, label)
    # ──────────────────────────────────────────────────────────────────────────

    @api.model
    def get_product_by_any_barcode(self, barcode):
        """
        Search all three barcode slots.
        Returns a dict:
          {
            'product_id': int,
            'product_tmpl_id': int,
            'qty': float,          # package quantity (1 for barcode_1)
            'label': str,          # package label
            'price': float,        # sales price × qty
          }
        or False when nothing is found.
        """
        if not barcode:
            return False

        # ── slot 1: standard Odoo barcode field (product.product level) ──────
        product = self.env['product.product'].search(
            [('barcode', '=', barcode)], limit=1
        )
        if product:
            return {
                'product_id': product.id,
                'product_tmpl_id': product.product_tmpl_id.id,
                'qty': 1.0,
                'label': product.name,
                'price': product.lst_price,
            }

        # ── slot 2 ────────────────────────────────────────────────────────────
        tmpl = self.search([('barcode_2', '=', barcode)], limit=1)
        if tmpl:
            qty = tmpl.package_qty_2 or 1.0
            label = tmpl.package_name_2 or (tmpl.name + ' (Pack 2)')
            return {
                'product_id': tmpl.product_variant_id.id,
                'product_tmpl_id': tmpl.id,
                'qty': qty,
                'label': label,
                'price': tmpl.list_price * qty,
            }

        # ── slot 3 ────────────────────────────────────────────────────────────
        tmpl = self.search([('barcode_3', '=', barcode)], limit=1)
        if tmpl:
            qty = tmpl.package_qty_3 or 1.0
            label = tmpl.package_name_3 or (tmpl.name + ' (Pack 3)')
            return {
                'product_id': tmpl.product_variant_id.id,
                'product_tmpl_id': tmpl.id,
                'qty': qty,
                'label': label,
                'price': tmpl.list_price * qty,
            }

        return False
