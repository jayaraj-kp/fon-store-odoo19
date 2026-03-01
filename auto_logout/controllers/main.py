from odoo import http
from odoo.http import request


class AutoLogoutController(http.Controller):

    @http.route('/auto_logout/config', type='json', auth='user')
    def get_auto_logout_config(self):
        """Return the auto logout delay (in minutes) for the current session."""
        delay = int(request.env['ir.config_parameter'].sudo().get_param(
            'auto_logout.delay', default=10
        ))
        return {'delay': delay}
