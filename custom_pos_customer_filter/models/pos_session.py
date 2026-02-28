from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_pos_ui_res_partner(self, params):
        # Override to show only child contacts + main customers
        params['search_params']['domain'] = [
            '|',
            ('parent_id', '!=', False),
            ('customer_rank', '>', 0),
        ]
        return super()._get_pos_ui_res_partner(params)