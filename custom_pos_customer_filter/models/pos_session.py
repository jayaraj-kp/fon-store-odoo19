from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        # Add filter: only load partners with customer_rank > 0
        # This excludes pure vendors and non-customer contacts
        result['search_params']['domain'].append(
            ('customer_rank', '>', 0)
        )
        return result