from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        _logger.warning("=== CUSTOM POS FILTER: _loader_params_res_partner CALLED ===")
        result = super()._loader_params_res_partner()
        _logger.warning("=== DOMAIN BEFORE: %s ===", result['search_params']['domain'])
        result['search_params']['domain'] = [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        _logger.warning("=== DOMAIN AFTER: %s ===", result['search_params']['domain'])
        return result

    def _get_pos_ui_res_partner(self, params):
        _logger.warning("=== CUSTOM POS FILTER: _get_pos_ui_res_partner CALLED ===")
        params['search_params']['domain'] = [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        _logger.warning("=== DOMAIN SET: %s ===", params['search_params']['domain'])
        return super()._get_pos_ui_res_partner(params)

    def _pos_data_process(self, loaded_data):
        _logger.warning("=== CUSTOM POS FILTER: _pos_data_process CALLED ===")
        super()._pos_data_process(loaded_data)
        if 'res.partner' in loaded_data:
            before_count = len(loaded_data['res.partner'])
            loaded_data['res.partner'] = [
                p for p in loaded_data['res.partner']
                if p.get('parent_id') or p.get('customer_rank', 0) > 0
            ]
            after_count = len(loaded_data['res.partner'])
            _logger.warning("=== PARTNERS: before=%s after=%s ===", before_count, after_count)
        else:
            _logger.warning("=== res.partner KEY NOT FOUND IN loaded_data ===")
            _logger.warning("=== AVAILABLE KEYS: %s ===", list(loaded_data.keys()))