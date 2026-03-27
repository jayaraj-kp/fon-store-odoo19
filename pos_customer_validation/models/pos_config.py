# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    require_customer_for_payment = fields.Boolean(
        string='Require Customer for Payment',
        default=True,
        help='If checked, customer selection will be mandatory before processing payments.'
    )

    payment_methods_requiring_customer = fields.Many2many(
        'pos.payment.method',
        string='Payment Methods Requiring Customer',
        help='Select which payment methods require customer selection. By default: Cash KDTY and Card KDTY'
    )
