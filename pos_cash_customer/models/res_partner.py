# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cash_customer = fields.Boolean(
        string='Is Cash Customer Master',
        default=False,
        help='Marks the master CASH CUSTOMER record'
    )

    @api.model
    def get_cash_customer_id(self):
        """Return the ID of the master CASH CUSTOMER partner."""
        cash_customer = self.search([('is_cash_customer', '=', True)], limit=1)
        if cash_customer:
            return cash_customer.id
        return False

    @api.model
    def _load_pos_data_fields(self, config_id):
        """
        Odoo 19 hook — extend the list of partner fields sent to POS.
        This ensures is_cash_customer and parent_id are available in JS.
        """
        params = super()._load_pos_data_fields(config_id)
        for field in ('is_cash_customer', 'parent_id', 'complete_name'):
            if field not in params:
                params.append(field)
        return params
