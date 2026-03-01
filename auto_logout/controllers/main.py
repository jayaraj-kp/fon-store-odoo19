from odoo import http
from odoo.http import request


class AutoLogoutController(http.Controller):

    @http.route('/auto_logout/config', type='json', auth='user')
    def get_auto_logout_config(self):
        delay = int(request.env['ir.config_parameter'].sudo().get_param(
            'auto_logout.delay', default=10
        ))
        return {'delay': delay}
