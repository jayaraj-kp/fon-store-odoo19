from odoo import models, fields


class PosOrder(models.Model):
    _inherit = 'pos.order'

    custom_receipt_note = fields.Char(
        string='Custom Receipt Note',
        help='Extra note to display on the POS receipt PDF'
    )
