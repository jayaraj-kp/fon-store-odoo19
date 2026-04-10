# -*- coding: utf-8 -*-
import logging
from odoo import models

_logger = logging.getLogger(__name__)

# Only these account types are P&L — safe to apply analytic
_PL_ACCOUNT_TYPES = {
    'income',
    'income_other',
    'expense',
    'expense_depreciation',
    'expense_direct_cost',
}

# These are balance sheet — must NEVER get analytic
# (receivable, payable, cash, bank, credit card, etc.)
_BLOCKED_ACCOUNT_TYPES = {
    'asset_receivable',
    'liability_payable',
    'asset_cash',
    'liability_credit_card',
    'asset_current',
    'liability_current',
}


def _get_pos_analytic(pos_config):
    """
    Resolve analytic account from a POS config by tracing:
        pos_config → picking_type_id → warehouse_id → analytic_account_id

    Falls back to a direct warehouse_id on pos.config if present.
    Returns False if nothing is configured.
    """
    # Try direct warehouse on pos.config (some versions expose this)
    wh = getattr(pos_config, 'warehouse_id', False)
    if wh and getattr(wh, 'analytic_account_id', False):
        return wh.analytic_account_id

    # Always-present path: via the stock operation type
    picking_type = getattr(pos_config, 'picking_type_id', False)
    if picking_type:
        wh = getattr(picking_type, 'warehouse_id', False)
        if wh and getattr(wh, 'analytic_account_id', False):
            return wh.analytic_account_id

    return False


def _is_pl_line(line):
    """Return True only for income/expense lines — never balance sheet."""
    if not line.account_id:
        return False
    return line.account_id.account_type in _PL_ACCOUNT_TYPES


def _apply_analytic_to_move(move, analytic, label=''):
    """
    Stamp analytic_distribution on every P&L line of an account.move.
    Skips lines that already carry this analytic.
    """
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(_is_pl_line):
        existing = line.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            line.analytic_distribution = new_dist
            _logger.debug(
                'POS analytic %s → %s line %s (%s)',
                analytic.name, label, line.id, line.account_id.code,
            )


class PosSession(models.Model):
    _inherit = 'pos.session'

    # ------------------------------------------------------------------
    # Hook 1 — standard session closing (Odoo 17/19 CE)
    # ------------------------------------------------------------------
    def _create_account_move(self, balancing_account, amount_to_balance,
                             bank_payment_method_diffs):
        result = super()._create_account_move(
            balancing_account, amount_to_balance, bank_payment_method_diffs
        )
        self._apply_pos_session_analytic()
        return result

    # ------------------------------------------------------------------
    # Hook 2 — alternate closing method name used in some builds
    # ------------------------------------------------------------------
    def close_pos_session(self):
        result = super().close_pos_session()
        self._apply_pos_session_analytic()
        return result

    # ------------------------------------------------------------------
    # Core application logic
    # ------------------------------------------------------------------
    def _apply_pos_session_analytic(self):
        """
        After the session closing journal entry is created, stamp the
        warehouse analytic account on every P&L line.

        Covers:
          1. The session summary move (self.move_id)
          2. Every individual order move inside the session
        """
        for session in self:
            analytic = _get_pos_analytic(session.config_id)
            if not analytic:
                _logger.debug(
                    'No analytic account on warehouse for POS config %s — skipping',
                    session.config_id.name,
                )
                continue

            # 1. Session closing / summary move
            _apply_analytic_to_move(session.move_id, analytic, label='session')

            # 2. Individual order moves (created per order or per session
            #    depending on the "journal entry" setting in POS config)
            for order in session.order_ids:
                _apply_analytic_to_move(
                    order.account_move, analytic, label='order'
                )


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # ------------------------------------------------------------------
    # Hook 3 — when a POS order is invoiced directly from the POS screen
    # ------------------------------------------------------------------
    def action_pos_order_invoice(self):
        result = super().action_pos_order_invoice()
        for order in self:
            analytic = _get_pos_analytic(order.session_id.config_id)
            if analytic:
                _apply_analytic_to_move(order.account_move, analytic, label='invoice')
        return result
