# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    require_customer_for_payment = fields.Boolean(
        string='Require Customer for Payment',
        default=True,
        help='If checked, customer selection will be mandatory before processing payments.'
    )
