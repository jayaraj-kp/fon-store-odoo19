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

    THE ONLY CORRECT PATH in Odoo 19 CE:
        pos_config.picking_type_id → warehouse_id → analytic_account_id

    WHY: pos_config.warehouse_id is a computed/related field that may return
    the company's default warehouse (e.g. CHELARI) for ALL configs, not the
    shop-specific warehouse. The picking_type_id is set per-shop in POS
    configuration and always points to the correct shop warehouse.

    DO NOT use pos_config.warehouse_id as primary lookup — it is unreliable.
    """
    # ── PRIMARY: picking_type_id → warehouse_id (shop-specific, always correct)
    picking_type = getattr(pos_config, 'picking_type_id', False)
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh:
            analytic = getattr(wh, 'analytic_account_id', False)
            if analytic:
                _logger.debug(
                    'POS analytic OK: config[%s] → picking_type[%s] → wh[%s] → analytic[%s]',
                    pos_config.name, picking_type.name, wh.name, analytic.name,
                )
                return analytic
            else:
                _logger.debug(
                    'POS analytic MISS: config[%s] → picking_type[%s] → wh[%s] has NO analytic',
                    pos_config.name, picking_type.name, wh.name,
                )
        else:
            _logger.debug(
                'POS analytic MISS: config[%s] → picking_type[%s] has NO warehouse',
                pos_config.name, picking_type.name,
            )
    else:
        _logger.warning(
            'POS analytic MISS: config[%s] has NO picking_type_id — '
            'set Operation Type in POS Configuration',
            pos_config.name,
        )

    # ── FALLBACK: direct warehouse_id on pos.config (less reliable)
    wh = getattr(pos_config, 'warehouse_id', False)
    if wh:
        analytic = getattr(wh, 'analytic_account_id', False)
        if analytic:
            _logger.warning(
                'POS analytic FALLBACK (may be wrong!): config[%s] → '
                'direct warehouse_id[%s] → analytic[%s]. '
                'Set picking_type_id on POS config for reliable resolution.',
                pos_config.name, wh.name, analytic.name,
            )
            return analytic

    return False


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on ALL lines of an account.move.
    Uses sudo() + check_move_validity=False so it works on posted/locked moves.
    Skips lines that already carry this specific analytic.
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
                    'POS analytic [%s] → %s line %s (%s)',
                    analytic.name, label, line.id, line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not apply analytic to %s line %s: %s',
                    label, line.id, e,
                )


def _apply_analytic_to_statement_lines(session, analytic):
    """
    Stamp analytic on bank statement line moves that belong to THIS session.
    Uses ONLY pos_session_id — never a broad journal search which would
    cross-contaminate sessions from different warehouses.
    """
    if not analytic:
        return
    st_lines = session.env['account.bank.statement.line'].search([
        ('pos_session_id', '=', session.id),
    ])
    if st_lines:
        for st_line in st_lines:
            if st_line.move_id:
                _apply_analytic_to_move(
                    st_line.move_id, analytic,
                    label='bank_stmt_%s' % st_line.move_id.name,
                )
    else:
        _logger.debug(
            'No statement lines found via pos_session_id=%s — '
            'bank_reconcile.py create() hook will handle them',
            session.id,
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
        Stamp the correct warehouse analytic on ALL journal entries of this
        POS session. Analytic comes from:
            session → config → picking_type_id → warehouse → analytic_account_id
        NOT from the logged-in user's warehouse.
        """
        for session in self:
            analytic = _get_pos_analytic(session.config_id)
            if not analytic:
                _logger.warning(
                    'No analytic for POS session [%s] config [%s] — '
                    'ensure the POS Operation Type warehouse has an Analytic Account set',
                    session.name, session.config_id.name,
                )
                continue

            # 1. Session summary move (POSS/)
            _apply_analytic_to_move(session.move_id, analytic, label='session')

            # 2. Order moves + payment moves
            for order in session.order_ids:
                _apply_analytic_to_move(order.account_move, analytic, label='order')
                for payment in order.payment_ids:
                    pay_move = getattr(payment, 'account_move_id', False)
                    if not pay_move:
                        pay_move = getattr(payment, 'move_id', False)
                    _apply_analytic_to_move(pay_move, analytic, label='payment')

            # 3. Bank statement line moves (CRDCH/, CSCHL/ etc.)
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