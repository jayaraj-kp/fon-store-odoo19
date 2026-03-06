from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_customer_id = fields.Many2one(
        'res.partner',
        string='POS Cash Customer',
        help='The master CASH CUSTOMER partner. All new POS customers will be added as contacts under this partner. Leave empty to use the standard create customer form.',
    )

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'pos_cash_customer.cash_customer_id',
            self.pos_cash_customer_id.id or 0
        )

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'pos_cash_customer.cash_customer_id', 0
        )
        try:
            partner_id = int(param)
        except (ValueError, TypeError):
            partner_id = 0
        res['pos_cash_customer_id'] = partner_id or False
        return res