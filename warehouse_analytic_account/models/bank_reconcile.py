# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


def _get_user_analytic(user):
    wh = _get_user_warehouse(user)
    if wh and wh.analytic_account_id:
        return wh.analytic_account_id
    return False


def _inject_analytic_into_data(data, analytic):
    """
    Inject the warehouse analytic account into every line of the
    reconcile_data_info 'data' list that does not already have one.
    This ensures it shows in the Analytic column of the reconcile widget.
    """
    if not data or not analytic:
        return data
    key = str(analytic.id)
    for line in data:
        existing = line.get('analytic_distribution') or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            line['analytic_distribution'] = new_dist
    return data


def _inject_analytic_into_reconcile_info(reconcile_info, analytic):
    """
    Given a full reconcile_data_info dict, inject analytic into all
    data lines and return the updated dict.
    """
    if not reconcile_info or not analytic:
        return reconcile_info
    data = reconcile_info.get('data', [])
    _inject_analytic_into_data(data, analytic)
    return reconcile_info


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # ------------------------------------------------------------------
    # Override _default_reconcile_data — called every time the reconcile
    # widget is opened or refreshed. Injecting here means the analytic
    # column is pre-filled the moment the user opens the statement line.
    # ------------------------------------------------------------------
    def _default_reconcile_data(self, from_unreconcile=False):
        result = super()._default_reconcile_data(from_unreconcile=from_unreconcile)
        analytic = _get_user_analytic(self.env.user)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    # ------------------------------------------------------------------
    # Override _recompute_suspense_line — called every time lines change
    # in the widget (add line, change amount, model applied, etc.)
    # ------------------------------------------------------------------
    def _recompute_suspense_line(self, data, reconcile_auxiliary_id,
                                 manual_reference):
        result = super()._recompute_suspense_line(
            data, reconcile_auxiliary_id, manual_reference
        )
        analytic = _get_user_analytic(self.env.user)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    # ------------------------------------------------------------------
    # Override reconcile_bank_line — called when user clicks Validate.
    # Stamps analytic on the actual posted journal entry lines after
    # reconciliation so it persists in the journal entry too.
    # ------------------------------------------------------------------
    def reconcile_bank_line(self):
        result = super().reconcile_bank_line()
        analytic = _get_user_analytic(self.env.user)
        if analytic:
            key = str(analytic.id)
            for st_line in self:
                if st_line.move_id:
                    for line in st_line.move_id.line_ids.filtered(
                        lambda l: l.account_id
                    ):
                        existing = line.analytic_distribution or {}
                        if key not in existing:
                            new_dist = dict(existing)
                            new_dist[key] = 100.0
                            try:
                                line.analytic_distribution = new_dist
                            except Exception as e:
                                _logger.warning(
                                    'Could not set analytic on reconcile line %s: %s',
                                    line.id, e
                                )
        return result

    # ------------------------------------------------------------------
    # Override _reconcile_data_by_model — called when a reconcile model
    # (auto-match rule) is applied to the statement line.
    # ------------------------------------------------------------------
    def _reconcile_data_by_model(self, data, reconcile_model,
                                 reconcile_auxiliary_id):
        new_data, new_id = super()._reconcile_data_by_model(
            data, reconcile_model, reconcile_auxiliary_id
        )
        analytic = _get_user_analytic(self.env.user)
        if analytic:
            _inject_analytic_into_data(new_data, analytic)
        return new_data, new_id

    # ------------------------------------------------------------------
    # Override _get_reconcile_line — called for every individual line
    # added to the reconcile widget (liquidity, counterpart, other).
    # ------------------------------------------------------------------
    def _get_reconcile_line(self, line, kind, is_counterpart=False,
                            max_amount=False, from_unreconcile=False,
                            reconcile_auxiliary_id=False, move=False,
                            is_reconciled=False):
        reconcile_auxiliary_id, lines = super()._get_reconcile_line(
            line, kind,
            is_counterpart=is_counterpart,
            max_amount=max_amount,
            from_unreconcile=from_unreconcile,
            reconcile_auxiliary_id=reconcile_auxiliary_id,
            move=move,
            is_reconciled=is_reconciled,
        )
        analytic = _get_user_analytic(self.env.user)
        if analytic:
            _inject_analytic_into_data(lines, analytic)
        return reconcile_auxiliary_id, lines
