# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_warehouse_analytic_account(self):
        """
        Return the analytic account linked to the current user's default
        warehouse, or False if none is configured.
        """
        user = self.env.user
        wh = getattr(user, 'property_warehouse_id', False)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """
        For every line in self that belongs to a posted / in-progress bill,
        stamp the warehouse analytic account in analytic_distribution if the
        line has a valid account.
        Works for both vendor bills (in_invoice) and vendor refunds (in_refund).
        """
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return

        for move in self:
            # Only apply to vendor bills / refunds
            if move.move_type not in ('in_invoice', 'in_refund'):
                continue

            for line in move.invoice_line_ids.filtered(
                lambda l: l.account_id and not l.display_type
            ):
                # analytic_distribution is a JSON dict  {analytic_account_id: percentage}
                existing = line.analytic_distribution or {}
                key = str(analytic_account.id)
                if key not in existing:
                    # Merge: keep existing accounts, add/overwrite warehouse account at 100 %
                    # If other analytic accounts are already present we add ours;
                    # adjust the percentage logic here if you need a different split.
                    new_distribution = dict(existing)
                    new_distribution[key] = 100.0
                    line.analytic_distribution = new_distribution
                    _logger.debug(
                        'Warehouse analytic %s applied to bill line %s',
                        analytic_account.name,
                        line.id,
                    )

    # ------------------------------------------------------------------
    # ORM hooks
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves._apply_warehouse_analytic_to_lines()
        return moves

    def write(self, vals):
        result = super().write(vals)
        # Re-apply when lines change or when the move is first saved as draft
        if any(
            k in vals
            for k in (
                'invoice_line_ids',
                'line_ids',
                'state',
                'move_type',
            )
        ):
            self._apply_warehouse_analytic_to_lines()
        return result

    def action_post(self):
        """Also apply right before posting to catch any last-minute line changes."""
        self._apply_warehouse_analytic_to_lines()
        return super().action_post()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # After line creation, re-trigger analytic application on the parent move
        moves = lines.move_id
        moves._apply_warehouse_analytic_to_lines()
        return lines
