from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Override confirm to block if any line price is below product cost.
        Only triggers on the Confirm button — no warnings on line save.
        """
        # Check if the feature is enabled in settings
        block_enabled = self.env['ir.config_parameter'].sudo().get_param(
            'sale_price_block.block_below_cost', default='True'
        )

        if block_enabled == 'True':
            for order in self:
                below_cost_lines = []

                for line in order.order_line:
                    if not line.product_id:
                        continue
                    cost_price = line.product_id.standard_price or 0.0
                    if line.price_unit < cost_price:
                        below_cost_lines.append({
                            'product': line.product_id.display_name,
                            'sale_price': line.price_unit,
                            'cost_price': cost_price,
                            'currency': order.currency_id.symbol or '',
                        })

                if below_cost_lines:
                    # Build a detailed error message listing all problematic lines
                    lines_detail = '\n'.join([
                        '  • %s  →  Sale Price: %s %.2f  |  Cost Price: %s %.2f' % (
                            item['product'],
                            item['currency'], item['sale_price'],
                            item['currency'], item['cost_price'],
                        )
                        for item in below_cost_lines
                    ])

                    raise UserError(
                        _(
                            'Cannot confirm sale order "%s".\n\n'
                            'The following product(s) have a unit price BELOW their cost price:\n\n'
                            '%s\n\n'
                            'Please update the sale prices before confirming the order.'
                        ) % (order.name, lines_detail)
                    )

        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_below_cost = fields.Boolean(
        string='Price Below Cost',
        compute='_compute_is_below_cost',
        store=False,
    )

    @api.depends('price_unit', 'product_id', 'product_id.standard_price')
    def _compute_is_below_cost(self):
        for line in self:
            if line.product_id:
                cost = line.product_id.standard_price or 0.0
                line.is_below_cost = line.price_unit < cost
            else:
                line.is_below_cost = False
