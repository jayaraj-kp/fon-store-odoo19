from odoo import models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        """
        Override _action_done to trigger custom cost recompute
        AFTER a stock move is completed (purchase receipt validated).

        Only fires for incoming moves (purchases/receipts), not sales/transfers.
        """
        res = super()._action_done(cancel_backorder=cancel_backorder)

        # Collect all products from incoming (purchase) moves that are now done
        incoming_products = self.env['product.product']

        for move in self:
            # picking_type_code == 'incoming' means this is a purchase receipt
            if (
                move.state == 'done'
                and move.picking_id
                and move.picking_id.picking_type_code == 'incoming'
                and move.product_id.use_custom_cost
            ):
                incoming_products |= move.product_id
                _logger.info(
                    "StockMove done (incoming): triggering custom cost "
                    "recompute for product [%s]",
                    move.product_id.display_name,
                )

        if incoming_products:
            incoming_products.recompute_custom_cost()

        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Also hook into button_validate on the picking (receipt),
        as a safety net in case _action_done is bypassed.
        """
        res = super().button_validate()

        # After validation, recompute for all custom-cost products in receipt
        if self.picking_type_code == 'incoming':
            products = self.move_ids.mapped('product_id').filtered(
                lambda p: p.use_custom_cost
            )
            if products:
                _logger.info(
                    "StockPicking validated: triggering custom cost recompute "
                    "for %s products.",
                    len(products),
                )
                products.recompute_custom_cost()

        return res


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """
        For PERIODIC valuation: the stock value is only updated when
        the vendor bill (account.move of type 'in_invoice') is confirmed.

        So we also hook here to recompute cost after bill posting,
        which updates standard_price used as the cost basis.
        """
        res = super().action_post()

        if self.move_type == 'in_invoice':
            # Get all products from bill lines
            products = self.invoice_line_ids.mapped('product_id').filtered(
                lambda p: p.use_custom_cost
            )
            if products:
                _logger.info(
                    "Vendor bill posted: triggering custom cost recompute "
                    "for %s products.",
                    len(products),
                )
                products.recompute_custom_cost()

        return res
