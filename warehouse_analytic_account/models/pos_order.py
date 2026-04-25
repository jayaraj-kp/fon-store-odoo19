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
    Resolve analytic account from a POS config by tracing:
        pos_config → picking_type_id → warehouse_id → analytic_account_id
    Falls back to a direct warehouse_id on pos.config if present.

    PRIORITY:
    1. picking_type_id → warehouse_id → analytic_account_id  (most reliable)
    2. warehouse_id directly on pos.config (if field exists)
    """
    # Priority 1: picking_type_id → warehouse (most reliable in Odoo 19)
    picking_type = getattr(pos_config, 'picking_type_id', False)
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug(
                'POS analytic resolved: config=%s picking_type=%s warehouse=%s analytic=%s',
                pos_config.name,
                picking_type.name,
                wh.name,
                wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # Priority 2: direct warehouse on pos.config (fallback)
    wh = getattr(pos_config, 'warehouse_id', False)
    if wh and getattr(wh, 'analytic_account_id', False):
        _logger.debug(
            'POS analytic resolved from direct warehouse: config=%s warehouse=%s analytic=%s',
            pos_config.name, wh.name, wh.analytic_account_id.name,
        )
        return wh.analytic_account_id

    _logger.warning(
        'POS analytic NOT resolved for config=%s (picking_type=%s)',
        pos_config.name,
        getattr(getattr(pos_config, 'picking_type_id', False), 'name', 'NONE'),
    )
    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on ALL lines of an account.move.
    Uses sudo() + check_move_validity=False for posted/locked moves.
    Skips lines that already carry this analytic.
    """
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
                _logger.debug(
                    'POS analytic %s → %s line %s (%s)',
                    analytic.name, label, line.id, line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to %s line %s: %s',
                    label, line.id, e,
                )


def _apply_analytic_to_statement_lines(session, analytic):
    """
    Stamp analytic on bank statement line moves (CRDCH/, CSCHL/ etc.)
    that belong to THIS session only.

    Searches ONLY by pos_session_id to avoid cross-contamination between
    different POS sessions/warehouses.
    """
    if not analytic:
        return

    env = session.env

    # Only use direct session link — never fall back to a broad journal search
    # which would match statement lines from OTHER warehouses' sessions
    st_lines = env['account.bank.statement.line'].search([
        ('pos_session_id', '=', session.id),
    ])

    if not st_lines:
        _logger.debug(
            'No bank statement lines found via pos_session_id for session %s — '
            'they will be stamped by bank_reconcile.py create() hook instead',
            session.name,
        )
        return

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
        """
        After session closing, stamp the correct warehouse analytic on ALL
        journal entry lines. The analytic comes from THIS session's POS config
        → picking_type → warehouse, NOT from the logged-in user's warehouse.

        Covers:
          1. Session closing / summary move (POSS/)
          2. Individual order moves (POSJ/ or INV/)
          3. Payment moves via order.payment_ids
          4. Bank statement line moves (CRDCH/, CSCHL/) via pos_session_id
        """
        for session in self:
            analytic = _get_pos_analytic(session.config_id)
            if not analytic:
                _logger.warning(
                    'No analytic configured for POS session %s (config: %s) — skipping',
                    session.name, session.config_id.name,
                )
                continue

            _logger.debug(
                'Applying POS analytic %s to session %s',
                analytic.name, session.name,
            )

            # 1. Session closing / summary move (POSS/ entry)
            _apply_analytic_to_move(session.move_id, analytic, label='session')

            # 2. Individual order moves + their payment moves
            for order in session.order_ids:
                _apply_analytic_to_move(
                    order.account_move, analytic, label='order'
                )
                for payment in order.payment_ids:
                    pay_move = getattr(payment, 'account_move_id', False)
                    if not pay_move:
                        pay_move = getattr(payment, 'move_id', False)
                    _apply_analytic_to_move(pay_move, analytic, label='payment')

            # 3. Bank statement line moves linked directly to this session
            _apply_analytic_to_statement_lines(session, analytic)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_invoice(self):
        """Apply analytic when a POS order is invoiced directly."""
        result = super().action_pos_order_invoice()
        for order in self:
            analytic = _get_pos_analytic(order.session_id.config_id)
            if analytic:
                _apply_analytic_to_move(
                    order.account_move, analytic, label='invoice'
                )
        return result