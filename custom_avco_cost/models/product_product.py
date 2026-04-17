from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Flag to enable/disable this custom costing per product
    use_custom_cost = fields.Boolean(
        string='Use Custom Cost (Value ÷ Latest Purchase Price)',
        default=False,
        help=(
            "When enabled, the product cost is automatically recalculated "
            "on every purchase using the formula:\n\n"
            "  Cost = Total Stock Value ÷ Latest Purchase Unit Price\n\n"
            "Example:\n"
            "  Old stock  : 50 qty × ₹200 = ₹10,000\n"
            "  New purchase: 100 qty × ₹250 = ₹25,000\n"
            "  Total Value : ₹35,000\n"
            "  Latest Price: ₹250\n"
            "  New Cost    : ₹35,000 ÷ ₹250 = ₹140"
        ),
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _get_latest_purchase_price(self):
        """
        Returns the unit price from the most recent confirmed
        purchase order line for this product.
        """
        self.ensure_one()
        # Search the latest confirmed PO line for this product
        po_line = self.env['purchase.order.line'].search(
            [
                ('product_id', '=', self.id),
                ('order_id.state', 'in', ['purchase', 'done']),
            ],
            order='order_id desc, id desc',
            limit=1,
        )
        if po_line:
            # Convert to product UoM if needed
            price = po_line.price_unit
            _logger.info(
                "Product [%s] latest purchase price = %s (PO: %s)",
                self.display_name, price, po_line.order_id.name,
            )
            return price
        return 0.0

    def _get_total_stock_value(self):
        """
        Returns the total stock value for this product.

        For PERIODIC valuation categories: computed manually as
        (qty_on_hand × standard_price) because no valuation layers exist.

        For PERPETUAL valuation categories: summed from
        stock.valuation.layer records.
        """
        self.ensure_one()
        categ = self.categ_id

        if categ.property_cost_method == 'standard' or \
                categ.property_valuation == 'manual_periodic':
            # Periodic: value = on-hand qty × current cost
            qty = self.qty_available
            cost = self.standard_price
            total = qty * cost
            _logger.info(
                "Product [%s] PERIODIC total value = %s qty × %s cost = %s",
                self.display_name, qty, cost, total,
            )
            return total
        else:
            # Perpetual: sum actual valuation layers
            layers = self.env['stock.valuation.layer'].search(
                [('product_id', '=', self.id)]
            )
            total = sum(layers.mapped('value'))
            _logger.info(
                "Product [%s] PERPETUAL total value from layers = %s",
                self.display_name, total,
            )
            return total

    def recompute_custom_cost(self):
        """
        Main method: recalculates and writes the new standard_price.

        New Cost = Total Stock Value ÷ Latest Purchase Unit Price

        Called automatically after every purchase receipt validation
        or vendor bill confirmation (see stock_move.py).
        Can also be called manually from the product form button.
        """
        for product in self:
            if not product.use_custom_cost:
                continue

            latest_price = product._get_latest_purchase_price()
            if not latest_price:
                _logger.warning(
                    "Product [%s] has no confirmed purchase orders yet. "
                    "Skipping custom cost recompute.",
                    product.display_name,
                )
                continue

            total_value = product._get_total_stock_value()

            if total_value <= 0:
                _logger.warning(
                    "Product [%s] total stock value is %s. "
                    "Skipping custom cost recompute.",
                    product.display_name, total_value,
                )
                continue

            new_cost = total_value / latest_price
            old_cost = product.standard_price

            _logger.info(
                "Product [%s] Custom Cost Recompute:\n"
                "  Total Value   : %s\n"
                "  Latest Price  : %s\n"
                "  New Cost      : %s  (was %s)",
                product.display_name,
                total_value, latest_price, new_cost, old_cost,
            )

            # Write via sudo to bypass potential access rules on cost field
            product.sudo().write({'standard_price': new_cost})

    def action_recompute_custom_cost(self):
        """Button action callable from product form view."""
        self.recompute_custom_cost()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Custom Cost Updated',
                'message': (
                    f'New cost for {self.display_name}: '
                    f'₹{self.standard_price:.4f}'
                ),
                'type': 'success',
                'sticky': False,
            },
        }
