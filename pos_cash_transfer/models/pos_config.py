from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allow_cash_transfer = fields.Boolean(
        string='Allow Cash Transfer Between Counters',
        default=True,
        help='Allow cashiers to transfer cash to other POS sessions'
    )
    cash_transfer_requires_manager = fields.Boolean(
        string='Require Manager Approval for Transfer',
        default=False,
        help='If enabled, only managers can approve cash transfers'
    )
