# # -*- coding: utf-8 -*-
# import logging
# from odoo import models
#
# _logger = logging.getLogger(__name__)
#
#
# def _get_pos_analytic(pos_config):
#     """
#     Resolve analytic account from a POS config by tracing:
#         pos_config → picking_type_id → warehouse_id → analytic_account_id
#     Falls back to a direct warehouse_id on pos.config if present.
#     Returns False if nothing is configured.
#     """
#     wh = getattr(pos_config, 'warehouse_id', False)
#     if wh and getattr(wh, 'analytic_account_id', False):
#         return wh.analytic_account_id
#
#     picking_type = getattr(pos_config, 'picking_type_id', False)
#     if picking_type:
#         wh = getattr(picking_type, 'warehouse_id', False)
#         if wh and getattr(wh, 'analytic_account_id', False):
#             return wh.analytic_account_id
#
#     return False
#
#
# def _apply_analytic_to_move(move, analytic, label=''):
#     """
#     Stamp analytic_distribution on ALL lines of an account.move
#     (including receivable, payable, cash, tax lines).
#     Skips lines that already carry this analytic.
#     """
#     if not move or not analytic:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             line.analytic_distribution = new_dist
#             _logger.debug(
#                 'POS analytic %s → %s line %s (%s)',
#                 analytic.name, label, line.id, line.account_id.code,
#             )
#
#
# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     def _create_account_move(self, balancing_account, amount_to_balance,
#                              bank_payment_method_diffs):
#         result = super()._create_account_move(
#             balancing_account, amount_to_balance, bank_payment_method_diffs
#         )
#         self._apply_pos_session_analytic()
#         return result
#
#     def close_pos_session(self):
#         result = super().close_pos_session()
#         self._apply_pos_session_analytic()
#         return result
#
#     def _apply_pos_session_analytic(self):
#         """
#         After session closing, stamp the warehouse analytic account on
#         ALL journal entry lines so every entry is fully tagged for
#         branch-level reporting.
#         Covers:
#           1. The session summary move (self.move_id)
#           2. Every individual order move inside the session
#           3. Payment account moves — found safely via order payment lines
#         """
#         for session in self:
#             analytic = _get_pos_analytic(session.config_id)
#             if not analytic:
#                 _logger.debug(
#                     'No analytic on warehouse for POS config %s — skipping',
#                     session.config_id.name,
#                 )
#                 continue
#
#             # 1. Session closing / summary move (POSS/ entry)
#             _apply_analytic_to_move(session.move_id, analytic, label='session')
#
#             # 2. Individual order moves + their payment moves
#             for order in session.order_ids:
#                 # Order account move (POSJ/ or INV/)
#                 _apply_analytic_to_move(
#                     order.account_move, analytic, label='order'
#                 )
#                 # Payment moves linked to this order — safe way without payment_ids
#                 for payment in order.payment_ids:
#                     pay_move = getattr(payment, 'account_move_id', False)
#                     if not pay_move:
#                         pay_move = getattr(payment, 'move_id', False)
#                     _apply_analytic_to_move(pay_move, analytic, label='payment')
#
#
# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     def action_pos_order_invoice(self):
#         """Apply analytic when a POS order is invoiced directly."""
#         result = super().action_pos_order_invoice()
#         for order in self:
#             analytic = _get_pos_analytic(order.session_id.config_id)
#             if analytic:
#                 _apply_analytic_to_move(
#                     order.account_move, analytic, label='invoice'
#                 )
#         return result

# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_pos_analytic(pos_config):
    _logger.warning('='*60)
    _logger.warning('POS ANALYTIC DEBUG: config=%s (id=%s)', pos_config.name, pos_config.id)

    # Log ALL fields on pos_config related to warehouse
    for fname in ('warehouse_id', 'picking_type_id', 'stock_location_id'):
        val = getattr(pos_config, fname, 'FIELD_NOT_EXIST')
        _logger.warning('  pos_config.%s = %s', fname, val)

    # Check picking_type_id path
    picking_type = getattr(pos_config, 'picking_type_id', False)
    _logger.warning('  picking_type_id: %s (id=%s)',
        getattr(picking_type, 'name', 'NONE'),
        getattr(picking_type, 'id', 'NONE'))

    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        _logger.warning('  picking_type.warehouse_id: %s (id=%s)',
            getattr(wh, 'name', 'NONE'),
            getattr(wh, 'id', 'NONE'))
        if wh:
            analytic = getattr(wh, 'analytic_account_id', False)
            _logger.warning('  picking_type.warehouse.analytic_account_id: %s (id=%s)',
                getattr(analytic, 'name', 'NONE'),
                getattr(analytic, 'id', 'NONE'))
            if analytic:
                _logger.warning('  RESULT: returning analytic from picking_type path: %s', analytic.name)
                _logger.warning('='*60)
                return analytic

    # Check direct warehouse_id path
    wh = getattr(pos_config, 'warehouse_id', False)
    _logger.warning('  direct warehouse_id: %s (id=%s)',
        getattr(wh, 'name', 'NONE'),
        getattr(wh, 'id', 'NONE'))
    if wh:
        analytic = getattr(wh, 'analytic_account_id', False)
        _logger.warning('  direct warehouse.analytic_account_id: %s (id=%s)',
            getattr(analytic, 'name', 'NONE'),
            getattr(analytic, 'id', 'NONE'))
        if analytic:
            _logger.warning('  RESULT: returning analytic from direct warehouse path: %s', analytic.name)
            _logger.warning('='*60)
            return analytic

    _logger.warning('  RESULT: NO analytic found!')
    _logger.warning('='*60)
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    if not move or not analytic:
        return
    key = str(analytic.id)
    _logger.warning('APPLY ANALYTIC: move=%s label=%s analytic=%s',
        getattr(move, 'name', '?'), label, analytic.name)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        _logger.warning('  line %s (%s): existing=%s',
            line.id, line.account_id.code, existing)
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
                _logger.warning('  line %s → SET to %s', line.id, new_dist)
            except Exception as e:
                _logger.warning('  line %s → FAILED: %s', line.id, e)
        else:
            _logger.warning('  line %s → SKIPPED (already has key %s)', line.id, key)


def _apply_analytic_to_statement_lines(session, analytic):
    if not analytic:
        return
    st_lines = session.env['account.bank.statement.line'].search([
        ('pos_session_id', '=', session.id),
    ])
    _logger.warning('STMT LINES for session %s (id=%s): found %s lines',
        session.name, session.id, len(st_lines))
    for st_line in st_lines:
        _logger.warning('  stmt_line id=%s move=%s journal=%s',
            st_line.id,
            getattr(st_line.move_id, 'name', 'NONE'),
            getattr(st_line.journal_id, 'name', 'NONE'))
        if st_line.move_id:
            _apply_analytic_to_move(
                st_line.move_id, analytic,
                label='bank_stmt_%s' % st_line.move_id.name,
            )


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _create_account_move(self, balancing_account, amount_to_balance,
                             bank_payment_method_diffs):
        result = super()._create_account_move(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )
        self._apply_pos_session_analytic()
        return result

    def close_pos_session(self):
        result = super().close_pos_session()
        self._apply_pos_session_analytic()
        return result

    def _apply_pos_session_analytic(self):
        for session in self:
            _logger.warning('SESSION ANALYTIC: session=%s config=%s',
                session.name, session.config_id.name)
            analytic = _get_pos_analytic(session.config_id)
            if not analytic:
                _logger.warning('SESSION ANALYTIC: NO analytic — skipping session %s', session.name)
                continue

            _apply_analytic_to_move(session.move_id, analytic, label='session')

            for order in session.order_ids:
                _apply_analytic_to_move(order.account_move, analytic, label='order')
                for payment in order.payment_ids:
                    pay_move = getattr(payment, 'account_move_id', False)
                    if not pay_move:
                        pay_move = getattr(payment, 'move_id', False)
                    _apply_analytic_to_move(pay_move, analytic, label='payment')

            _apply_analytic_to_statement_lines(session, analytic)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_invoice(self):
        result = super().action_pos_order_invoice()
        for order in self:
            _logger.warning('POS ORDER INVOICE: order=%s session=%s config=%s',
                order.name,
                getattr(order.session_id, 'name', '?'),
                getattr(order.session_id.config_id, 'name', '?'))
            analytic = _get_pos_analytic(order.session_id.config_id)
            if analytic:
                _apply_analytic_to_move(order.account_move, analytic, label='invoice')
        return result