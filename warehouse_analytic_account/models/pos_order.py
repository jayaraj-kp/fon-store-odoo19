# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    """Helper function to get the default warehouse from user across Odoo versions."""
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_warehouse_analytic_account(self):
        """Get the analytic account from the user's default warehouse."""
        wh = _get_user_warehouse(self.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """
        Apply warehouse analytic account to all POS order lines.
        This ensures analytic tracking from point of sale through to accounting.
        """
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return

        key = str(analytic_account.id)
        for order in self:
            for line in order.lines:
                existing = line.analytic_distribution or {}
                if key not in existing:
                    new_dist = dict(existing)
                    new_dist[key] = 100.0
                    line.analytic_distribution = new_dist
                    _logger.debug(
                        'Warehouse analytic %s applied to POS line %s',
                        analytic_account.name, line.id,
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Apply warehouse analytic when POS order is created."""
        orders = super().create(vals_list)
        orders._apply_warehouse_analytic_to_lines()
        return orders

    def write(self, vals):
        """Re-apply warehouse analytic when order lines are modified."""
        result = super().write(vals)
        if 'lines' in vals:
            self._apply_warehouse_analytic_to_lines()
        return result

    def action_pos_order_paid(self):
        """Apply warehouse analytic before marking order as paid."""
        self._apply_warehouse_analytic_to_lines()
        return super().action_pos_order_paid()


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Apply warehouse analytic when order lines are created."""
        lines = super().create(vals_list)
        if lines:
            lines.order_id._apply_warehouse_analytic_to_lines()
        return lines

    def write(self, vals):
        """Re-apply warehouse analytic when order line details change."""
        result = super().write(vals)
        if any(k in vals for k in ('product_id', 'qty', 'price_unit', 'analytic_distribution')):
            self.order_id._apply_warehouse_analytic_to_lines()
        return result

    @api.onchange('product_id')
    def _onchange_product_apply_warehouse_analytic(self):
        """
        When product is selected in POS, immediately apply warehouse analytic.
        This provides real-time feedback in the POS interface.
        """
        wh = _get_user_warehouse(self.env.user)
        if not wh or not wh.analytic_account_id:
            return

        key = str(wh.analytic_account_id.id)
        existing = self.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            self.analytic_distribution = new_dist