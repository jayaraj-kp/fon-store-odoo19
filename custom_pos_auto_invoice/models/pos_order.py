from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    """
    Server-side safety net:
    Forces to_invoice = True for every POS order that has a partner set.
    Orders without a partner cannot be invoiced (Odoo standard behaviour),
    so we only force it when a partner exists.
    """

    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        # Only force invoice if a partner is present
        if fields.get('partner_id'):
            fields['to_invoice'] = True
        return fields
