# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcode_prefix = fields.Char(
        string='Barcode Prefix',
        config_parameter='product_barcode_autogen.barcode_prefix',
        default='BC',
        help='Prefix to use for auto-generated barcodes (e.g. "BC" → BC-A1B2C3D4E5F6).',
    )
    barcode_length = fields.Integer(
        string='Barcode Random Part Length',
        config_parameter='product_barcode_autogen.barcode_length',
        default=12,
        help='Number of random alphanumeric characters after the prefix (4–20).',
    )
