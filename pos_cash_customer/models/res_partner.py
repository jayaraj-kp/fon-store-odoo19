# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cash_customer = fields.Boolean(
        string='Is Cash Customer',
        default=False,
        help='Mark this partner as the default POS Cash Customer.',
    )

    @api.model
    def create_from_pos_simplified(self, vals):
        """
        Called from POS UI simplified contact creation popup.
        Creates a partner with the provided vals and returns the created partner data.
        """
        # Ensure customer rank
        vals.setdefault('customer_rank', 1)
        partner = self.create(vals)
        return {
            'id': partner.id,
            'name': partner.name,
            'phone': partner.phone or '',
            'email': partner.email or '',
            'street': partner.street or '',
            'city': partner.city or '',
            'country_id': [partner.country_id.id, partner.country_id.name] if partner.country_id else False,
            'barcode': partner.barcode or '',
        }
