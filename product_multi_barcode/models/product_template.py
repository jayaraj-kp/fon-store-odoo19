# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    barcode_2 = fields.Char(string='Barcode 2', copy=False, index=True)
    package_qty_2 = fields.Float(string='Package Qty 2', default=0.0)
    package_name_2 = fields.Char(string='Pack 2 Label')

    barcode_3 = fields.Char(string='Barcode 3', copy=False, index=True)
    package_qty_3 = fields.Float(string='Package Qty 3', default=0.0)
    package_name_3 = fields.Char(string='Pack 3 Label')

    @api.constrains('barcode_2')
    def _check_barcode_2_unique(self):
        for rec in self:
            if not rec.barcode_2:
                continue
            if self.search([('barcode_2', '=', rec.barcode_2), ('id', '!=', rec.id)], limit=1):
                raise ValidationError(
                    _('Barcode 2 "%s" is already used by another product.') % rec.barcode_2)

    @api.constrains('barcode_3')
    def _check_barcode_3_unique(self):
        for rec in self:
            if not rec.barcode_3:
                continue
            if self.search([('barcode_3', '=', rec.barcode_3), ('id', '!=', rec.id)], limit=1):
                raise ValidationError(
                    _('Barcode 3 "%s" is already used by another product.') % rec.barcode_3)
