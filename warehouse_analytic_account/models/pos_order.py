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
import logging
from odoo import models

_logger = logging.getLogger(__name__)


def _get_pos_analytic(pos_config):
    """
    Resolve analytic account from a POS config.

    PROBLEM FOUND IN LOGS:
        FON-STORE KONDOTTY → picking_type='PoS Orders'(id=9) → warehouse=CHELARI-SHOP(id=1)
        The KONDOTTY POS config is using CHELARI's operation type — misconfiguration.

    SOLUTION: Try multiple paths in order of reliability:
    1. Search stock.warehouse directly by matching the POS config's session name prefix
       or by finding the warehouse whose short name matches the config's name
    2. picking_type_id → warehouse_id  (works IF correctly configured)
    3. Direct warehouse_id on pos.config (fallback)

    The KEY insight: we match POS config to warehouse by searching warehouses
    whose analytic account exists and whose name/short_name appears in the
    POS config name — e.g. "FON-STORE KONDOTTY" contains "KDTY" or "KONDOTTY".
    """
    _logger.warning('POS ANALYTIC: config=%s (id=%s)', pos_config.name, pos_config.id)

    env = pos_config.env

    # ── STRATEGY 1: Match warehouse by name substring in POS config name ──────
    # e.g. "FON-STORE KONDOTTY" → find warehouse where short_name "KDTY" or
    # name "KONDOTTY-SHOP" is contained in config name
    warehouses = env['stock.warehouse'].search([
        ('analytic_account_id', '!=', False),
        ('company_id', '=', pos_config.company_id.id),
    ])
    _logger.warning('  Warehouses with analytic: %s', [(w.name, w.code) for w in warehouses])

    config_name_upper = pos_config.name.upper()
    for wh in warehouses:
        wh_name_upper = wh.name.upper()
        wh_code_upper = (wh.code or '').upper()
        # Check if warehouse name or code appears in POS config name
        if wh_name_upper in config_name_upper or (wh_code_upper and wh_code_upper in config_name_upper):
            _logger.warning(
                '  STRATEGY 1 MATCH: config[%s] contains wh name/code [%s/%s] → analytic=%s',
                pos_config.name, wh.name, wh.code, wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # ── STRATEGY 2: picking_type_id → warehouse_id ────────────────────────────
    picking_type = getattr(pos_config, 'picking_type_id', False)
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        _logger.warning('  STRATEGY 2: picking_type=%s → wh=%s',
            getattr(picking_type, 'name', 'NONE'), getattr(wh, 'name', 'NONE'))
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.warning('  STRATEGY 2 RESULT: %s', wh.analytic_account_id.name)
            return wh.analytic_account_id

    # ── STRATEGY 3: direct warehouse_id on pos.config ─────────────────────────
    wh = getattr(pos_config, 'warehouse_id', False)
    _logger.warning('  STRATEGY 3: direct wh=%s', getattr(wh, 'name', 'NONE'))
    if wh and getattr(wh, 'analytic_account_id', False):
        _logger.warning('  STRATEGY 3 RESULT: %s', wh.analytic_account_id.name)
        return wh.analytic_account_id

    _logger.warning('  NO analytic found for config %s', pos_config.name)
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
                _logger.debug('POS analytic [%s] → %s line %s (%s)',
                    analytic.name, label, line.id, line.account_id.code)
            except Exception as e:
                _logger.warning('Could not apply analytic to %s line %s: %s', label, line.id, e)


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
        result = super().action_pos_order_invoice()
        for order in self:
            analytic = _get_pos_analytic(order.session_id.config_id)
            if analytic:
                _apply_analytic_to_move(order.account_move, analytic, label='invoice')
        return result