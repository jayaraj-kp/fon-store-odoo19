# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        """
        Add our custom fields to the partner data loaded when POS starts.
        This ensures pos_unique_id and pos_config_id are available
        in the POS JavaScript partner objects.
        """
        result = super()._loader_params_res_partner()
        extra_fields = ['pos_unique_id', 'pos_config_id']
        existing = result.get('search_params', {}).get('fields', [])
        for f in extra_fields:
            if f not in existing:
                existing.append(f)
        result.setdefault('search_params', {})['fields'] = existing
        return result

    def _pos_data_process(self, loaded_data):
        """
        Also include shop_code in the POS config data so the frontend
        knows the prefix for displaying/creating customer IDs.
        """
        result = super()._pos_data_process(loaded_data)
        return result

    # ── Make shop_code available in POS config ────────────────────────────
    def _get_pos_ui_pos_config(self, params):
        """Ensure shop_code is included when the POS config is sent to the UI."""
        configs = super()._get_pos_ui_pos_config(params)
        # shop_code is a regular field on pos.config, it will be auto-included
        # if listed in the fields param. We force-add it here for safety.
        for config in configs:
            if 'shop_code' not in config:
                pos_config = self.env['pos.config'].browse(config.get('id'))
                config['shop_code'] = pos_config.shop_code or ''
        return configs
