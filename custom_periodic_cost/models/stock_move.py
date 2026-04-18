from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            # Trigger only on incoming receipt moves
            if move.picking_code == 'incoming' and move.product_id:
                product = move.product_id

                # 1. Calculation: (Remaining Qty * Current Cost) + (New Qty * Purchase Price)
                # We subtract move.quantity because it has already been added to qty_available
                previous_qty = product.qty_available - move.quantity

                # Use current standard_price as the "Previous Cost"
                total_value = (previous_qty * product.standard_price) + (move.quantity * move.price_unit)

                # 2. Update the Cost Price (standard_price)
                if product.qty_available > 0:
                    new_avco = total_value / product.qty_available
                    product.sudo().write({'standard_price': new_avco})
        return res