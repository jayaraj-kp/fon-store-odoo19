# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Add latest-price-based cost field to product template."""

    _inherit = 'product.template'

    latest_price_unit_cost = fields.Float(
        string='Latest Price Unit Cost',
        digits='Product Price',
        readonly=True,
        help=(
            "Custom unit cost = Total Stock Value / Latest Purchase Price.\n\n"
            "Formula:\n"
            "  Total Stock Value  = Standard Cost (AVCO) x Qty on Hand\n"
            "  Latest Purchase Price = Unit price on the most recent confirmed PO line\n\n"
            "Example:\n"
            "  50 qty @ 200 + 100 qty @ 250 = 35,000 total value\n"
            "  Latest purchase price = 250\n"
            "  Latest Price Unit Cost = 35,000 / 250 = 140"
        ),
    )


class PurchaseOrder(models.Model):
    """Scheduled action: recompute latest_price_unit_cost for all products."""

    _inherit = 'purchase.order'

    @api.model
    def _compute_latest_price_unit_cost(self):
        """
        For every storable product that has at least one confirmed PO line:

          latest_price_unit_cost = (standard_price * qty_on_hand) / latest_po_price

        standard_price  --> AVCO cost maintained by Odoo (total value / total qty)
        qty_on_hand     --> sum of on-hand quantities across all locations
        latest_po_price --> price_unit from the most recent confirmed/done PO line

        If latest_po_price is 0 or no PO exists, the field is left unchanged (0).
        """
        POLine = self.env['purchase.order.line']
        ProductTemplate = self.env['product.template']

        # All storable product templates (type = 'consu' covers storable in Odoo 17+,
        # but we check both to be safe across minor version differences).
        storable_tmpls = ProductTemplate.search([
            ('type', 'in', ('product', 'consu')),
        ])

        for tmpl in storable_tmpls:
            # Aggregate qty on hand across all product variants.
            qty_on_hand = sum(
                tmpl.mapped('product_variant_ids.qty_available')
            )

            # Total stock value = AVCO standard_price * qty on hand.
            # standard_price is the AVCO running cost maintained by Odoo.
            total_value = tmpl.standard_price * qty_on_hand

            if total_value <= 0:
                tmpl.latest_price_unit_cost = 0.0
                continue

            # Latest confirmed PO line for any variant of this template.
            latest_line = POLine.search([
                ('product_id.product_tmpl_id', '=', tmpl.id),
                ('order_id.state', 'in', ('purchase', 'done')),
                ('product_qty', '>', 0),
            ], order='date_order desc, id desc', limit=1)

            if not latest_line or latest_line.price_unit <= 0:
                tmpl.latest_price_unit_cost = 0.0
                continue

            latest_po_price = latest_line.price_unit
            tmpl.latest_price_unit_cost = total_value / latest_po_price
