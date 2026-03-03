# from odoo import fields, models
#
#
# class PosConfig(models.Model):
#     _inherit = 'pos.config'
#
#     upi_vpa = fields.Char(
#         string='UPI ID (VPA)',
#         help='Your UPI Virtual Payment Address e.g. yourstore@paytm or 9876543210@ybl',
#     )
#     upi_merchant_name = fields.Char(
#         string='UPI Merchant Name',
#         help='Name displayed to customer on their UPI app during payment',
#     )
#     upi_qr_on_receipt = fields.Boolean(
#         string='Show UPI QR Code on Receipt',
#         default=False,
#         help='Print a dynamic UPI QR code on each receipt with the exact bill amount',
#     )
# pos_config.py
from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    upi_vpa = fields.Char(
        string='UPI ID (VPA)',
        help='Your UPI Virtual Payment Address e.g. yourstore@paytm or 9876543210@ybl',
    )
    upi_merchant_name = fields.Char(
        string='UPI Merchant Name',
        help='Name displayed to customer on their UPI app during payment',
    )
    upi_qr_on_receipt = fields.Boolean(
        string='Show UPI QR Code on Receipt',
        default=False,
        help='Print a dynamic UPI QR code on each receipt with the exact bill amount',
    )

    def _get_fields_for_pos(self):
        fields = super()._get_fields_for_pos()
        fields += ['upi_vpa', 'upi_merchant_name', 'upi_qr_on_receipt']
        return fields