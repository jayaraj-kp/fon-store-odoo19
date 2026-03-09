# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    default_cash_customer_id = fields.Many2one(
        'res.partner',
        string='Default Cash Customer',
        help='This customer will be pre-selected on every new POS order.',
        domain=[('customer_rank', '>', 0)],
    )

    @api.model
    def _get_cash_customer(self):
        """Return the default CASH CUSTOMER partner, creating if needed."""
        partner = self.env.ref(
            'pos_cash_customer.partner_cash_customer', raise_if_not_found=False
        )
        if not partner:
            partner = self.env['res.partner'].search(
                [('name', '=', 'CASH CUSTOMER')], limit=1
            )
        return partner

    def get_pos_ui_pos_config(self, params):
        """Extend config data sent to POS UI."""
        result = super().get_pos_ui_pos_config(params)
        cash_customer = self._get_cash_customer()
        if cash_customer:
            result['cash_customer_id'] = cash_customer.id
            result['cash_customer_name'] = cash_customer.name
        return result
