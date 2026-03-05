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
    def create_from_pos_with_cash_parent(self, partner_vals):
        """
        Called from POS JS when creating a new customer.
        Automatically sets parent_id to the CASH CUSTOMER if not already set.
        """
        cash_customer = self.search([('is_cash_customer', '=', True)], limit=1)
        if cash_customer and not partner_vals.get('parent_id'):
            partner_vals['parent_id'] = cash_customer.id
            # When a parent is set, type should be 'contact'
            partner_vals.setdefault('type', 'contact')

        partner = self.create(partner_vals)
        return partner.read(self._load_pos_data_fields(None))[0]

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Fields needed by POS for partner records."""
        return [
            'id', 'name', 'street', 'city', 'state_id', 'country_id',
            'vat', 'lang', 'phone', 'zip', 'mobile', 'email',
            'barcode', 'write_date', 'property_product_pricelist',
            'parent_id', 'is_cash_customer', 'type', 'complete_name',
        ]
