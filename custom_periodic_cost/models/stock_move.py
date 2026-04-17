from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            # Trigger only on incoming products (Receipts)
            if move.picking_code == 'incoming' and move.product_id:
                product = move.product_id

                # 1. Get the price from the CURRENT receipt (the one you just validated)
                # This ensures we use the "Latest Purchase Price"
                latest_purchase_price = move.price_unit or move.purchase_line_id.price_unit

                # 2. Calculate Total Value MANUALLY
                # Formula: (Previous Qty * Previous Cost) + (New Received Qty * New Price)
                previous_qty = product.qty_available - move.quantity
                previous_cost = product.standard_price

                new_received_qty = move.quantity
                new_received_price = latest_purchase_price

                total_value = (previous_qty * previous_cost) + (new_received_qty * new_received_price)

                # 3. Apply your custom formula: Total Value / Latest Purchase Price
                # Scenario: (50 * 200) + (100 * 250) = 35,000
                # Result: 35,000 / 250 = 140
                if latest_purchase_price > 0:
                    custom_cost = total_value / latest_purchase_price

                    # Update the product cost field
                    product.sudo().write({'standard_price': custom_cost})

        return res