from odoo import http
from odoo.http import request


class PosCashTransferController(http.Controller):

    @http.route('/pos/cash_transfer/get_sessions',
                type='json', auth='user', methods=['POST'])
    def get_open_sessions(self, current_session_id):
        # Full sudo() on env so ALL related field reads (pos.config, res.users)
        # bypass access checks for restricted POS employee users
        env = request.env(su=True)
        sessions = env['pos.session'].search([
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
        env = request.env(su=True)
        return env['pos.cash.transfer'].create_transfer_from_pos(
            from_session_id, to_session_id, amount, reason)
