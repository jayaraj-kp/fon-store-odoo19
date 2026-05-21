#
# import logging
# from odoo import models
#
# _logger = logging.getLogger(__name__)
#
#
# def _match_warehouse_by_name(warehouses, name_to_match):
#     """
#     Find the best-matching warehouse by comparing meaningful words
#     between the warehouse name and the target string.
#
#     Scoring:
#     - +1 for each word (>=4 chars) shared between warehouse name and target
#     - +1 if warehouse short code appears in target
#     - Tiebreak: fewer unmatched words in warehouse name = more specific = winner
#
#     Returns the best warehouse record or False.
#     """
#     if not name_to_match:
#         return False
#
#     target_upper = name_to_match.upper()
#     target_words = set(w for w in target_upper.replace('-', ' ').split() if len(w) >= 4)
#
#     best_wh = False
#     best_score = 0
#     best_unmatched = 999
#
#     for wh in warehouses:
#         wh_name_upper = wh.name.upper()
#         wh_code_upper = (wh.code or '').upper()
#         wh_words = set(w for w in wh_name_upper.replace('-', ' ').split() if len(w) >= 4)
#
#         common = target_words & wh_words
#         code_match = wh_code_upper and wh_code_upper in target_upper
#         score = len(common) + (1 if code_match else 0)
#         unmatched = len(wh_words - target_words)
#
#         if score > best_score or (score == best_score and score > 0 and unmatched < best_unmatched):
#             best_score = score
#             best_unmatched = unmatched
#             best_wh = wh
#
#     if best_score > 0:
#         _logger.debug('Warehouse match: "%s" → %s (score=%s)', name_to_match, best_wh.name, best_score)
#         return best_wh
#     return False
#
#
# def _get_pos_analytic(pos_config):
#     """
#     Resolve analytic account from a POS config.
#
#     Strategy:
#     1. Match warehouse by scoring word overlap between POS config name
#        and warehouse name — e.g. "FON-STORE KONDOTTY" → "KONDOTTY-SHOP"
#     2. picking_type_id → warehouse_id (unreliable if misconfigured)
#     3. Direct warehouse_id on pos.config (fallback)
#     """
#     env = pos_config.env
#     company_id = pos_config.company_id.id
#
#     warehouses = env['stock.warehouse'].search([
#         ('analytic_account_id', '!=', False),
#         ('company_id', '=', company_id),
#     ])
#
#     # Strategy 1: name word matching
#     wh = _match_warehouse_by_name(warehouses, pos_config.name)
#     if wh:
#         _logger.debug('POS analytic STRATEGY 1: config[%s] → wh[%s] → %s',
#             pos_config.name, wh.name, wh.analytic_account_id.name)
#         return wh.analytic_account_id
#
#     # Strategy 2: picking_type_id → warehouse
#     picking_type = getattr(pos_config, 'picking_type_id', False)
#     if picking_type:
#         wh = getattr(picking_type, 'warehouse_id', False)
#         if wh and getattr(wh, 'analytic_account_id', False):
#             _logger.debug('POS analytic STRATEGY 2: config[%s] → picking_type → wh[%s] → %s',
#                 pos_config.name, wh.name, wh.analytic_account_id.name)
#             return wh.analytic_account_id
#
#     # Strategy 3: direct warehouse_id
#     wh = getattr(pos_config, 'warehouse_id', False)
#     if wh and getattr(wh, 'analytic_account_id', False):
#         _logger.debug('POS analytic STRATEGY 3: config[%s] → direct wh[%s] → %s',
#             pos_config.name, wh.name, wh.analytic_account_id.name)
#         return wh.analytic_account_id
#
#     _logger.warning('POS analytic: no match for config[%s]', pos_config.name)
#     return False
#
#
# def _apply_analytic_to_move(move, analytic, label=''):
#     if not move or not analytic:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             try:
#                 line.sudo().with_context(
#                     check_move_validity=False,
#                     skip_account_move_synchronization=True,
#                 ).analytic_distribution = new_dist
#             except Exception as e:
#                 _logger.warning('Could not apply analytic to %s line %s: %s', label, line.id, e)
#
#
# def _apply_analytic_to_statement_lines(session, analytic):
#     if not analytic:
#         return
#     st_lines = session.env['account.bank.statement.line'].search([
#         ('pos_session_id', '=', session.id),
#     ])
#     for st_line in st_lines:
#         if st_line.move_id:
#             _apply_analytic_to_move(st_line.move_id, analytic,
#                 label='bank_stmt_%s' % st_line.move_id.name)
#
#
# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     def _create_account_move(self, balancing_account, amount_to_balance,
#                              bank_payment_method_diffs):
#         result = super()._create_account_move(
#             balancing_account, amount_to_balance, bank_payment_method_diffs)
#         self._apply_pos_session_analytic()
#         return result
#
#     def close_pos_session(self):
#         result = super().close_pos_session()
#         self._apply_pos_session_analytic()
#         return result
#
#     def _apply_pos_session_analytic(self):
#         for session in self:
#             analytic = _get_pos_analytic(session.config_id)
#             if not analytic:
#                 _logger.warning('No analytic for session %s', session.name)
#                 continue
#             _apply_analytic_to_move(session.move_id, analytic, label='session')
#             for order in session.order_ids:
#                 _apply_analytic_to_move(order.account_move, analytic, label='order')
#                 for payment in order.payment_ids:
#                     pay_move = getattr(payment, 'account_move_id', False)
#                     if not pay_move:
#                         pay_move = getattr(payment, 'move_id', False)
#                     _apply_analytic_to_move(pay_move, analytic, label='payment')
#             _apply_analytic_to_statement_lines(session, analytic)
#
#
# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     def action_pos_order_invoice(self):
#         result = super().action_pos_order_invoice()
#         for order in self:
#             analytic = _get_pos_analytic(order.session_id.config_id)
#             if analytic:
#                 _apply_analytic_to_move(order.account_move, analytic, label='invoice')
#         return result

# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _match_warehouse_by_name(warehouses, name_to_match):
    """
    Find the best-matching warehouse by comparing meaningful words
    between the warehouse name and the target string.

    Scoring:
    - +1 for each word (>=4 chars) shared between warehouse name and target
    - +1 if warehouse short code appears in target
    - Tiebreak: fewer unmatched words in warehouse name = more specific = winner

    Returns the best warehouse record or False.
    """
    if not name_to_match:
        return False

    target_upper = name_to_match.upper()
    target_words = set(w for w in target_upper.replace('-', ' ').split() if len(w) >= 4)

    best_wh = False
    best_score = 0
    best_unmatched = 999

    for wh in warehouses:
        wh_name_upper = wh.name.upper()
        wh_code_upper = (wh.code or '').upper()
        wh_words = set(w for w in wh_name_upper.replace('-', ' ').split() if len(w) >= 4)

        common = target_words & wh_words
        code_match = wh_code_upper and wh_code_upper in target_upper
        score = len(common) + (1 if code_match else 0)
        unmatched = len(wh_words - target_words)

        if score > best_score or (score == best_score and score > 0 and unmatched < best_unmatched):
            best_score = score
            best_unmatched = unmatched
            best_wh = wh

    if best_score > 0:
        _logger.debug('Warehouse match: "%s" → %s (score=%s)', name_to_match, best_wh.name, best_score)
        return best_wh
    return False


def _get_pos_analytic(pos_config):
    """
    Resolve analytic account from a POS config.

    Strategy:
    1. Match warehouse by scoring word overlap between POS config name
       and warehouse name — e.g. "FON-STORE KONDOTTY" → "KONDOTTY-SHOP"
    2. picking_type_id → warehouse_id (unreliable if misconfigured)
    3. Direct warehouse_id on pos.config (fallback)
    """
    env = pos_config.env
    company_id = pos_config.company_id.id

    warehouses = env['stock.warehouse'].search([
        ('analytic_account_id', '!=', False),
        ('company_id', '=', company_id),
    ])

    # Strategy 1: name word matching
    wh = _match_warehouse_by_name(warehouses, pos_config.name)
    if wh:
        _logger.debug('POS analytic STRATEGY 1: config[%s] → wh[%s] → %s',
            pos_config.name, wh.name, wh.analytic_account_id.name)
        return wh.analytic_account_id

    # Strategy 2: picking_type_id → warehouse
    picking_type = getattr(pos_config, 'picking_type_id', False)
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug('POS analytic STRATEGY 2: config[%s] → picking_type → wh[%s] → %s',
                pos_config.name, wh.name, wh.analytic_account_id.name)
            return wh.analytic_account_id

    # Strategy 3: direct warehouse_id
    wh = getattr(pos_config, 'warehouse_id', False)
    if wh and getattr(wh, 'analytic_account_id', False):
        _logger.debug('POS analytic STRATEGY 3: config[%s] → direct wh[%s] → %s',
            pos_config.name, wh.name, wh.analytic_account_id.name)
        return wh.analytic_account_id

    _logger.warning('POS analytic: no match for config[%s]', pos_config.name)
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on ALL lines of an account.move.
    Uses sudo() + context flags to bypass posted-move restrictions.
    Skips lines that already carry this analytic.
    """
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        if existing.get(key) != 100.0 or len(existing) > 1:
            new_dist = {key: 100.0}
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
                _logger.debug(
                    'POS analytic %s → %s line %s (%s)',
                    analytic.name, label, line.id,
                    line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to %s line %s: %s',
                    label, line.id, e,
                )


def _apply_analytic_to_statement_lines(session, analytic):
    if not analytic:
        return
    st_lines = session.env['account.bank.statement.line'].search([
        ('pos_session_id', '=', session.id),
    ])
    for st_line in st_lines:
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
            balancing_account, amount_to_balance, bank_payment_method_diffs)
        self._apply_pos_session_analytic()
        return result

    def close_pos_session(self):
        result = super().close_pos_session()
        self._apply_pos_session_analytic()
        return result

    def _apply_pos_session_analytic(self):
        for session in self:
            analytic = _get_pos_analytic(session.config_id)
            if not analytic:
                _logger.warning('No analytic for session %s', session.name)
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
        """
        Apply analytic when a POS order is invoiced directly.

        The key fix: Odoo creates and immediately posts the invoice inside
        super().action_pos_order_invoice(). The receivable/payable lines are
        only finalised during action_post(), so they are NOT yet present when
        the move is first created.  We therefore apply the analytic AFTER
        super() returns — at which point the move is already in 'posted' state
        and ALL lines (including receivable 121000) exist and can be tagged.

        sudo() + context flags bypass the "cannot edit a posted move" guard.
        """
        result = super().action_pos_order_invoice()

        for order in self:
            analytic = _get_pos_analytic(order.session_id.config_id)
            if not analytic:
                _logger.warning(
                    'POS analytic: no analytic for order %s (config: %s)',
                    order.name, order.session_id.config_id.name,
                )
                continue

            move = order.account_move
            if not move:
                _logger.warning(
                    'POS analytic: no account_move on order %s after invoicing',
                    order.name,
                )
                continue

            _logger.debug(
                'POS invoice analytic: applying %s to move %s (state=%s, lines=%s)',
                analytic.name, move.name, move.state, len(move.line_ids),
            )
            _apply_analytic_to_move(move, analytic, label='pos_invoice')

        return result