# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def get_cash_customer_info(self):
        """Called from POS frontend to get the master CASH CUSTOMER partner id."""
        partner = self.env['res.partner'].get_cash_customer_partner()
        return {
            'id': partner.id,
            'name': partner.name,
        }
