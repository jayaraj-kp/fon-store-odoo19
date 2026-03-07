# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Store which barcode slot was used so it can be printed / tracked
    scanned_barcode = fields.Char(string='Scanned Barcode', copy=False)
    package_label = fields.Char(string='Package Label', copy=False)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def add_product_by_barcode(self, order_id, barcode):
        """
        Called from a wizard or barcode button in the sale order.
        Resolves any of the 3 barcode slots and adds/updates a sale line.
        """
        order = self.browse(order_id)
        if not order:
            return {'error': 'Order not found'}

        result = self.env['product.template'].get_product_by_any_barcode(barcode)
        if not result:
            return {'error': 'No product found for barcode: %s' % barcode}

        product = self.env['product.product'].browse(result['product_id'])
        qty = result['qty']
        label = result['label']

        # look for an existing line with the same product + same scanned barcode
        existing_line = order.order_line.filtered(
            lambda l: l.product_id.id == product.id
            and l.scanned_barcode == barcode
        )
        if existing_line:
            existing_line[0].product_uom_qty += qty
        else:
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': product.lst_price,
                'scanned_barcode': barcode,
                'package_label': label,
            })

        return {'success': True, 'qty': qty, 'label': label}
