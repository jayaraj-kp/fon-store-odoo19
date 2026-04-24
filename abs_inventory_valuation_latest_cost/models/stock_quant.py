# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018-Today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from odoo import api, fields, models, _


class StockQuant(models.Model):
    """Extend stock.quant to add latest purchase cost field."""

    _inherit = "stock.quant"

    latest_purchase_cost = fields.Float(
        string='Latest Purchase Cost',
        help="Total inventory value based on the latest confirmed purchase price "
             "(Latest Unit Price × Quantity on Hand).",
        digits='Account',
        readonly=True,
    )


class PurchaseOrderOfStock(models.Model):
    """Extend purchase.order to compute latest purchase cost on stock quants."""

    _inherit = "purchase.order"

    @api.model
    def _set_latest_cost(self):
        """Scheduled action: update latest_purchase_cost on all stock.quant records.

        Algorithm
        ---------
        For every product that has at least one confirmed/done purchase order line,
        find the order line with the most recent *order date* and use its unit
        price to value the current on-hand quantity stored in stock.quant.

        Changes from the original (Odoo 12) implementation
        ---------------------------------------------------
        * ``qty`` field renamed to ``quantity`` in Odoo 16+.
        * ``date_order`` on ``purchase.order.line`` is now a related field that
          mirrors ``order_id.date_order``; comparison with ``False`` / ``0`` has
          been replaced by a proper ``False``-safe comparison.
        * Removed the inner ``stock_product`` loop that redundantly re-searched
          inside an already-iterated loop (caused duplicate writes and wrong
          values when a product had quants in multiple locations).
        * Used ``mapped`` and SQL-ordered search to simplify the "latest line"
          lookup instead of a manual Python max loop.
        """

        PurchaseOrderLine = self.env['purchase.order.line']
        StockQuant = self.env['stock.quant']

        # Fetch all confirmed/done purchase order lines in one query.
        confirmed_lines = PurchaseOrderLine.search([
            ('order_id.state', 'in', ('purchase', 'done')),
            ('product_id', '!=', False),
        ])

        if not confirmed_lines:
            return

        # Collect unique products.
        products = confirmed_lines.mapped('product_id')

        for product in products:
            # Get the line with the latest order date for this product.
            # Ordering by date_order desc + id desc ensures determinism when
            # two lines share the same timestamp.
            latest_line = PurchaseOrderLine.search([
                ('product_id', '=', product.id),
                ('order_id.state', 'in', ('purchase', 'done')),
                ('product_qty', '>', 0),
            ], order='date_order desc, id desc', limit=1)

            if not latest_line:
                continue

            unit_price = latest_line.price_unit

            # Update every quant that holds this product.
            quants = StockQuant.search([('product_id', '=', product.id)])
            for quant in quants:
                quant.latest_purchase_cost = quant.quantity * unit_price
