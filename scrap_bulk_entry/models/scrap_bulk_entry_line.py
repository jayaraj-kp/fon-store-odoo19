# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ScrapBulkEntryLine(models.Model):
    _name = 'scrap.bulk.entry.line'
    _description = 'Scrap Bulk Entry Line'

    bulk_entry_id = fields.Many2one(
        'scrap.bulk.entry',
        string='Bulk Entry',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['consu', 'product'])],
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        help='If empty, the source location of the bulk entry will be used.',
    )
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial Number',
        domain="[('product_id', '=', product_id)]",
    )
    company_id = fields.Many2one(
        related='bulk_entry_id.company_id',
        store=True,
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.lot_id = False
        else:
            self.product_uom_id = False

    @api.onchange('bulk_entry_id')
    def _onchange_bulk_entry_id(self):
        """Pre-fill location from parent if set."""
        if self.bulk_entry_id and self.bulk_entry_id.location_id:
            self.location_id = self.bulk_entry_id.location_id
