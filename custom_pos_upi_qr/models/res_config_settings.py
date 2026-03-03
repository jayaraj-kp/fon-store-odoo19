from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_upi_vpa = fields.Char(
        string='UPI ID (VPA)',
        related='pos_config_id.upi_vpa',
        readonly=False,
    )
    pos_upi_merchant_name = fields.Char(
        string='UPI Merchant Name',
        related='pos_config_id.upi_merchant_name',
        readonly=False,
    )
    pos_upi_qr_on_receipt = fields.Boolean(
        string='Show UPI QR Code on Receipt',
        related='pos_config_id.upi_qr_on_receipt',
        readonly=False,
    )
