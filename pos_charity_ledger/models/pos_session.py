# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    charity_donation_total = fields.Float(
        string='Total Charity Donations',
        compute='_compute_charity_totals',
        store=True,
    )
    charity_donation_count = fields.Integer(
        string='Number of Donations',
        compute='_compute_charity_totals',
        store=True,
    )

    @api.depends('order_ids')
    def _compute_charity_totals(self):
        for session in self:
            donations = self.env['pos.charity.donation'].search([
                ('pos_session_id', '=', session.id),
                ('state', '=', 'confirmed'),
            ])
            session.charity_donation_total = sum(donations.mapped('amount'))
            session.charity_donation_count = len(donations)

    def _loader_params_pos_config(self):
        """Load charity config into POS frontend."""
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend([
            'charity_enabled',
            'charity_account_id',
            'charity_button_label',
        ])
        return result

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('pos.charity.account')
        return result

    def _loader_params_pos_charity_account(self):
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name', 'description'],
            }
        }
