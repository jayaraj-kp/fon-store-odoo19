from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load):
        result = super().load_data(models_to_load)
        if 'res.partner' in result:
            result['res.partner'] = [
                p for p in result['res.partner']
                if p.get('parent_id') or p.get('customer_rank', 0) > 0
            ]
        return result