# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_cash_customer = fields.Boolean(
        string='Is Cash Customer',
        default=False,
    )

    @api.model
    def _cleanup_duplicate_cash_customers(self):
        """Remove duplicate CASH CUSTOMER records, keeping only the xmlid one."""
        try:
            canonical = self.env.ref(
                'pos_cash_customer.partner_cash_customer', raise_if_not_found=False
            )
            duplicates = self.search([
                ('name', '=', 'CASH CUSTOMER'),
                ('is_cash_customer', '=', True),
            ])
            if canonical:
                duplicates = duplicates.filtered(lambda p: p.id != canonical.id)
            elif duplicates:
                # Keep the first one
                duplicates = duplicates[1:]

            if duplicates:
                duplicates.write({'active': False})
        except Exception as e:
            pass  # Don't break installation

    @api.model
    def create_from_pos_simplified(self, vals):
        """Called from POS simplified contact creation popup."""
        vals.setdefault('customer_rank', 1)
        partner = self.create(vals)
        return {
            'id': partner.id,
            'name': partner.name,
            'phone': partner.phone or '',
            'email': partner.email or '',
            'street': partner.street or '',
            'city': partner.city or '',
        }
