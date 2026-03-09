# -*- coding: utf-8 -*-
from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _get_cash_customer(self):
        partner = self.env.ref(
            'pos_cash_customer.partner_cash_customer', raise_if_not_found=False
        )
        if not partner:
            partner = self.env['res.partner'].search(
                [('name', '=', 'CASH CUSTOMER'), ('is_cash_customer', '=', True)], limit=1
            )
        return partner

    def get_pos_ui_pos_config(self, params):
        result = super().get_pos_ui_pos_config(params)
        # Cleanup duplicates silently on each POS open
        self.env['res.partner']._cleanup_duplicate_cash_customers()
        cash_customer = self._get_cash_customer()
        if cash_customer:
            result['cash_customer_id'] = cash_customer.id
            result['cash_customer_name'] = cash_customer.name
        return result
