# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
#
# class POSOrder(models.Model):
#     _inherit = 'pos.order'
#
#     def action_pos_order_paid(self):
#         """
#         Override payment to block if any line price is below product cost.
#         Uses same setting as sale orders for unified control.
#         """
#         # Check if the feature is enabled in settings
#         block_enabled = self.env['ir.config_parameter'].sudo().get_param(
#             'sale_price_block.block_below_cost', default='True'
#         )
#
#         if block_enabled == 'True':
#             for order in self:
#                 below_cost_lines = []
#
#                 for line in order.lines:
#                     if not line.product_id:
#                         continue
#                     cost_price = line.product_id.standard_price or 0.0
#                     if line.price_unit < cost_price:
#                         below_cost_lines.append({
#                             'product': line.product_id.display_name,
#                             'sale_price': line.price_unit,
#                             'cost_price': cost_price,
#                             'currency': order.currency_id.symbol or '',
#                         })
#
#                 if below_cost_lines:
#                     # Build a detailed error message listing all problematic lines
#                     lines_detail = '\n'.join([
#                         '  • %s  →  Sale Price: %s %.2f  |  Cost Price: %s %.2f' % (
#                             item['product'],
#                             item['currency'], item['sale_price'],
#                             item['currency'], item['cost_price'],
#                         )
#                         for item in below_cost_lines
#                     ])
#
#                     raise UserError(
#                         _(
#                             'Cannot process POS order "%s".\n\n'
#                             'The following product(s) have a unit price BELOW their cost price:\n\n'
#                             '%s\n\n'
#                             'Please update the sale prices before proceeding to payment.'
#                         ) % (order.name, lines_detail)
#                     )
#
#         return super().action_pos_order_paid()