from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _get_pos_ui_pos_config(self, params):
        result = super()._get_pos_ui_pos_config(params)
        # Inject cash_customer_id into POS config data
        cash_customer_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'pos_cash_customer.cash_customer_id', 0
            )
        )
        result['cash_customer_id'] = cash_customer_id
        return result
