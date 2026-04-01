# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

# Resolve the warehouse field name once at import time
_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    """Return the default warehouse for a user, regardless of Odoo version."""
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_warehouse_analytic_account(self):
        """Return the analytic account linked to the current user's default warehouse."""
        wh = _get_user_warehouse(self.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """
        Stamp the warehouse analytic account into analytic_distribution on
        every non-section invoice line that has an account set.
        Works for vendor bills (in_invoice) and vendor refunds (in_refund).
        """
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return

        key = str(analytic_account.id)
        for move in self:
            if move.move_type not in ('in_invoice', 'in_refund'):
                continue
            for line in move.invoice_line_ids.filtered(
                lambda l: l.account_id and not l.display_type
            ):
                existing = line.analytic_distribution or {}
                if key not in existing:
                    new_dist = dict(existing)
                    new_dist[key] = 100.0
                    line.analytic_distribution = new_dist
                    _logger.debug(
                        'Warehouse analytic %s applied to bill line %s',
                        analytic_account.name, line.id,
                    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_warehouse_analytic_to_lines()
        return moves

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ('invoice_line_ids', 'line_ids', 'state', 'move_type')):
            self._apply_warehouse_analytic_to_lines()
        return result

    def action_post(self):
        """Apply right before posting to catch any last-minute line changes."""
        self._apply_warehouse_analytic_to_lines()
        return super().action_post()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.move_id._apply_warehouse_analytic_to_lines()
        return lines

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ('account_id', 'product_id')):
            self.move_id._apply_warehouse_analytic_to_lines()
        return result

    @api.onchange('product_id', 'account_id')
    def _onchange_product_apply_warehouse_analytic(self):
        """
        Fires immediately in the UI when the user selects a product or account —
        fills analytic_distribution on the spot without needing to save first.
        """
        if not self.move_id or self.move_id.move_type not in ('in_invoice', 'in_refund'):
            return
        wh = _get_user_warehouse(self.env.user)
        if not wh or not wh.analytic_account_id:
            return
        key = str(wh.analytic_account_id.id)
        existing = self.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            self.analytic_distribution = new_dist
