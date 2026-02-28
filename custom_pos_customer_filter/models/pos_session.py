from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        # Filter partners after loading
        loaded_data['res.partner'] = [
            p for p in loaded_data.get('res.partner', [])
            if p.get('parent_id') or p.get('customer_rank', 0) > 0
        ]