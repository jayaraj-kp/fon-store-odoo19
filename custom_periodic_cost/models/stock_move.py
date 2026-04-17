from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        # Run the standard Odoo logic first
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        for move in self:
            # Only trigger for incoming products (Receipts)
            if move.picking_code == 'incoming' and move.product_id:
                product = move.product_id

                # 1. Find the latest Purchase Price for this product
                last_po_line = self.env['purchase.order.line'].search([
                    ('product_id', '=', product.id),
                    ('state', 'in', ['purchase', 'done'])
                ], order='id desc', limit=1)

                latest_price = last_po_line.price_unit if last_po_line else product.standard_price

                # 2. Calculate Total Value (Current On-Hand * Current Cost)
                # Before this receipt, the value was 10,000.
                # After receipt of 100 units at 250, the standard AVCO value is 35,000.
                total_stock_value = product.qty_available * product.standard_price

                # 3. Apply your custom formula: Total Value / Latest Purchase Price
                if latest_price > 0:
                    # Logic: 35,000 / 250 = 140
                    custom_cost = total_stock_value / latest_price

                    # Force write the new cost to the product
                    product.sudo().write({'standard_price': custom_cost})

        return res