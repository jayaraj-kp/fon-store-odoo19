from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()

        # Show ONLY child contacts (partners that have a parent)
        # These are the contacts created inside the Contacts tab
        result['search_params']['domain'] = [
            ('parent_id', '!=', False),
        ]
        return result