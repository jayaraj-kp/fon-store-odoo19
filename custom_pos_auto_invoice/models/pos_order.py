from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    """
    Server-side safety net:
    Even if the JS flag is missed for any reason, the server will
    still mark every POS order as 'to_invoice = True' so an
    accounting invoice is always generated after payment.

    If the order has no partner set, it silently skips invoice
    creation rather than crashing (Odoo's default behaviour).
    """

    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        """
        Called by sync_from_ui / create_from_ui.
        Force to_invoice = True on every incoming POS order.
        """
        fields = super()._order_fields(ui_order)
        fields['to_invoice'] = True
        return fields

    # ------------------------------------------------------------------
    # Optional: auto-action invoice immediately after order is saved
    # Uncomment the block below if you want the invoice to be
    # CONFIRMED (not just flagged) right after payment syncs.
    # ------------------------------------------------------------------
    # @api.model
    # def create_from_ui(self, orders, draft=False):
    #     order_ids = super().create_from_ui(orders, draft=draft)
    #     for rec in self.browse([o['id'] for o in order_ids]):
    #         try:
    #             if rec.to_invoice and rec.partner_id and rec.state == 'paid':
    #                 rec._generate_pos_order_invoice()
    #         except Exception as e:
    #             _logger.warning("Auto-invoice failed for POS order %s: %s", rec.name, e)
    #     return order_ids
