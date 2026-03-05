# -*- coding: utf-8 -*-
from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        """Ensure res.partner is loaded with extra fields."""
        data = super()._load_pos_data_models(config_id)
        return data

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        return result

    def _loader_params_res_partner(self):
        """Extend partner loader to include cash customer info."""
        result = super()._loader_params_res_partner()
        # Make sure is_cash_customer is included in fields
        if 'fields' in result.get('search_params', {}):
            fields = result['search_params']['fields']
            if 'is_cash_customer' not in fields:
                fields.append('is_cash_customer')
            if 'parent_id' not in fields:
                fields.append('parent_id')
        return result
