# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Pack 2
    barcode_2 = fields.Char(
        string='Barcode 2', copy=False, index=True,
        help='Barcode for Pack 2 (e.g. 1 dozen)',
    )
    package_qty_2 = fields.Float(
        string='Package Qty 2', digits='Product Unit of Measure', default=0.0,
        help='Units in this pack. E.g. 12 for a dozen.',
    )
    package_name_2 = fields.Char(
        string='Pack 2 Label', help='e.g. Dozen',
    )

    # Pack 3
    barcode_3 = fields.Char(
        string='Barcode 3', copy=False, index=True,
        help='Barcode for Pack 3 (e.g. big carton)',
    )
    package_qty_3 = fields.Float(
        string='Package Qty 3', digits='Product Unit of Measure', default=0.0,
        help='Units in this pack. E.g. 120 for a big carton.',
    )
    package_name_3 = fields.Char(
        string='Pack 3 Label', help='e.g. Big Carton',
    )

    @api.constrains('barcode_2')
    def _check_barcode_2_unique(self):
        for rec in self:
            if not rec.barcode_2:
                continue
            if self.search([('barcode_2', '=', rec.barcode_2), ('id', '!=', rec.id)], limit=1):
                raise ValidationError(_('Barcode 2 "%s" is already used by another product.') % rec.barcode_2)
            if self.search([('barcode', '=', rec.barcode_2)], limit=1):
                raise ValidationError(_('Barcode 2 "%s" is already used as a main barcode.') % rec.barcode_2)

    @api.constrains('barcode_3')
    def _check_barcode_3_unique(self):
        for rec in self:
            if not rec.barcode_3:
                continue
            if self.search([('barcode_3', '=', rec.barcode_3), ('id', '!=', rec.id)], limit=1):
                raise ValidationError(_('Barcode 3 "%s" is already used by another product.') % rec.barcode_3)
            if self.search([('barcode', '=', rec.barcode_3)], limit=1):
                raise ValidationError(_('Barcode 3 "%s" is already used as a main barcode.') % rec.barcode_3)

    @api.model
    def get_product_by_any_barcode(self, barcode):
        """Returns dict with product_id, qty, label, price — or False."""
        if not barcode:
            return False
        # slot 1
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            return {'product_id': product.id, 'qty': 1.0, 'label': product.name, 'price': product.lst_price}
        # slot 2
        tmpl = self.search([('barcode_2', '=', barcode)], limit=1)
        if tmpl:
            qty = tmpl.package_qty_2 or 1.0
            return {'product_id': tmpl.product_variant_id.id, 'qty': qty,
                    'label': tmpl.package_name_2 or (tmpl.name + ' Pack2'),
                    'price': tmpl.list_price * qty}
        # slot 3
        tmpl = self.search([('barcode_3', '=', barcode)], limit=1)
        if tmpl:
            qty = tmpl.package_qty_3 or 1.0
            return {'product_id': tmpl.product_variant_id.id, 'qty': qty,
                    'label': tmpl.package_name_3 or (tmpl.name + ' Pack3'),
                    'price': tmpl.list_price * qty}
        return False
