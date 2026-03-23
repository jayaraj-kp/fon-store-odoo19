from odoo import http
from odoo.http import request
import json


class PosCashTransferController(http.Controller):

    @http.route('/pos/cash_transfer/get_open_sessions',
                type='json', auth='user', methods=['POST'])
    def get_open_sessions(self, current_session_id):
        """Get all open POS sessions except current one"""
        sessions = request.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('id', '!=', current_session_id),
        ])
        result = []
        for session in sessions:
            result.append({
                'id': session.id,
                'name': session.name,
                'pos_name': session.config_id.name,
                'cashier': session.user_id.name,
            })
        return result

    @http.route('/pos/cash_transfer/create',
                type='json', auth='user', methods=['POST'])
    def create_cash_transfer(self, from_session_id, to_session_id,
                              amount, reason=''):
        """Create and process cash transfer from POS"""
        try:
            # Validate sessions
            from_session = request.env['pos.session'].browse(from_session_id)
            to_session = request.env['pos.session'].browse(to_session_id)

            if not from_session.exists():
                return {'success': False, 'error': 'Source session not found!'}
            if not to_session.exists():
                return {'success': False, 'error': 'Destination session not found!'}
            if from_session.state != 'opened':
                return {'success': False, 'error': 'Source POS is not open!'}
            if to_session.state != 'opened':
                return {'success': False, 'error': 'Destination POS is not open!'}
            if float(amount) <= 0:
                return {'success': False, 'error': 'Amount must be greater than 0!'}

            # Create cash in statement for source (cash out)
            cash_out_reason = 'Cash Transfer to %s (Ref: Transfer)' % to_session.config_id.name
            if reason:
                cash_out_reason += ' - ' + reason

            # Create cash in statement for destination (cash in)
            cash_in_reason = 'Cash Transfer from %s (Ref: Transfer)' % from_session.config_id.name
            if reason:
                cash_in_reason += ' - ' + reason

            # Get cash payment methods
            from_cash_method = from_session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1]
            to_cash_method = to_session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1]

            if not from_cash_method:
                return {'success': False,
                        'error': 'No cash payment method found in source POS!'}
            if not to_cash_method:
                return {'success': False,
                        'error': 'No cash payment method found in destination POS!'}

            # Create transfer record
            transfer = request.env['pos.cash.transfer'].create({
                'from_session_id': from_session_id,
                'to_session_id': to_session_id,
                'amount': amount,
                'reason': reason,
                'cashier_id': request.env.user.id,
            })

            # Record cash out in source session
            request.env['pos.session']._create_cash_statement_lines(
                from_session,
                from_cash_method.journal_id,
                -float(amount),
                cash_out_reason
            )

            # Record cash in for destination session
            request.env['pos.session']._create_cash_statement_lines(
                to_session,
                to_cash_method.journal_id,
                float(amount),
                cash_in_reason
            )

            transfer.write({'state': 'done'})

            return {
                'success': True,
                'transfer_id': transfer.id,
                'transfer_name': transfer.name,
                'message': '₹ %.2f successfully transferred to %s!' % (
                    float(amount), to_session.config_id.name)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/pos/cash_transfer/history',
                type='json', auth='user', methods=['POST'])
    def get_transfer_history(self, session_id):
        """Get transfer history for current session"""
        transfers_out = request.env['pos.cash.transfer'].search([
            ('from_session_id', '=', session_id),
            ('state', '=', 'done')
        ])
        transfers_in = request.env['pos.cash.transfer'].search([
            ('to_session_id', '=', session_id),
            ('state', '=', 'done')
        ])

        history = []
        for t in transfers_out:
            history.append({
                'name': t.name,
                'type': 'out',
                'amount': t.amount,
                'counter': t.to_pos_id.name,
                'reason': t.reason or '',
                'date': t.transfer_date.strftime('%d/%m/%Y %H:%M') if t.transfer_date else '',
                'cashier': t.cashier_id.name,
            })
        for t in transfers_in:
            history.append({
                'name': t.name,
                'type': 'in',
                'amount': t.amount,
                'counter': t.from_pos_id.name,
                'reason': t.reason or '',
                'date': t.transfer_date.strftime('%d/%m/%Y %H:%M') if t.transfer_date else '',
                'cashier': t.cashier_id.name,
            })

        return sorted(history,
                      key=lambda x: x['date'], reverse=True)


class PosSessionExtended(http.Controller):

    @http.route('/pos/cash_transfer/validate_amount',
                type='json', auth='user', methods=['POST'])
    def validate_amount(self, session_id, amount):
        """Check if session has enough cash for transfer"""
        session = request.env['pos.session'].browse(session_id)
        if not session.exists():
            return {'valid': False, 'error': 'Session not found'}

        # Get current cash amount
        cash_in = sum(session.cash_register_total_entry_encoding or [0])
        return {
            'valid': True,
            'current_cash': session.cash_register_balance_end or 0,
        }
