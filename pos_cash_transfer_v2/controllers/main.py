from odoo import http
from odoo.http import request


class PosCashTransferController(http.Controller):

    @http.route('/pos/cash_transfer/get_sessions',
                type='json', auth='user', methods=['POST'])
    def get_open_sessions(self, current_session_id):
        sessions = request.env['pos.session'].sudo().search([
            ('state', '=', 'opened'),
            ('id', '!=', current_session_id),
        ])
        return [{
            'id': s.id,
            'name': s.name,
            'pos_name': s.config_id.name,
            'cashier': s.user_id.name,
        } for s in sessions]

    @http.route('/pos/cash_transfer/process',
                type='json', auth='user', methods=['POST'])
    def process_transfer(self, from_session_id, to_session_id,
                         amount, reason=''):
        return request.env['pos.cash.transfer'].sudo().create_transfer_from_pos(
            from_session_id, to_session_id, amount, reason)
