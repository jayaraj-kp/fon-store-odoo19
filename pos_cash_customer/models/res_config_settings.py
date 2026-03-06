from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_customer_id = fields.Many2one(
        'res.partner',
        string='POS Cash Customer',
        config_parameter='pos_cash_customer.cash_customer_id',
        # Removed domain restriction - allow any partner (company or individual)
        help='The master CASH CUSTOMER partner. All new POS customers will be added as contacts under this partner.',
    )