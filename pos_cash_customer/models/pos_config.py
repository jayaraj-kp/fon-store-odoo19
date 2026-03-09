# -*- coding: utf-8 -*-
from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _get_cash_customer(self):
        """Return the default CASH CUSTOMER partner."""
        partner = self.env.ref(
            'pos_cash_customer.partner_cash_customer', raise_if_not_found=False
        )
        if not partner:
            partner = self.env['res.partner'].search(
                [('name', '=', 'CASH CUSTOMER')], limit=1
            )
        return partner

    def get_pos_ui_pos_config(self, params):
        """Extend config data sent to POS UI with cash customer id."""
        result = super().get_pos_ui_pos_config(params)
        cash_customer = self._get_cash_customer()
        if cash_customer:
            result['cash_customer_id'] = cash_customer.id
            result['cash_customer_name'] = cash_customer.name
        return result
