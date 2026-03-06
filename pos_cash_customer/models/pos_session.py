from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    cash_customer_id = fields.Integer(
        string='Cash Customer ID',
        compute='_compute_cash_customer_id',
    )

    def _compute_cash_customer_id(self):
        param = self.env['ir.config_parameter'].sudo().get_param(
            'pos_cash_customer.cash_customer_id', '0'
        )
        try:
            cash_id = int(param)
        except (ValueError, TypeError):
            cash_id = 0
        for config in self:
            config.cash_customer_id = cash_id