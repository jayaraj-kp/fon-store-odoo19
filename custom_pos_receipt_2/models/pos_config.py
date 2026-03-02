from odoo import models, fields

class PosConfig(models.Model):
    _inherit = 'pos.config'

    qr_code_size = fields.Integer(
        string='QR Code Size (px)',
        default=80,
        help='Set the QR code size in pixels for POS receipt'
    )