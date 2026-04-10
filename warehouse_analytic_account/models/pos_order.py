# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    """
    Safely retrieve user's default warehouse from various field names.
    Handles compatibility across Odoo versions.
    """
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_warehouse_analytic_account(self):
        """
        Retrieve the analytic account from the user's default warehouse.
        Falls back to session's location warehouse if user warehouse not found.
        """
        # Try user's default warehouse first
        wh = _get_user_warehouse(self.env.user)

        # If no user warehouse, try session's location warehouse
        if not wh and self.session_id and self.session_id.config_id:
            location = self.session_id.config_id.stock_location_id
            if location and location.warehouse_id:
                wh = location.warehouse_id

        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    def _apply_warehouse_analytic_to_lines(self):
        """
        Stamp warehouse analytic account on all POS order lines.
        Applies 100% distribution to each line.

        Note: In Odoo 19 POS, we safely handle both old-style (lines_ids)
        and new-style field access patterns.
        """
        analytic_account = self._get_warehouse_analytic_account()
        if not analytic_account:
            return

        key = str(analytic_account.id)
        for order in self:
            # Safely get order lines - check both possible field names
            lines = False
            if hasattr(order, 'lines_ids') and order.lines_ids:
                lines = order.lines_ids

            if not lines:
                # Field might not exist or might be empty
                _logger.debug('No order lines found for POS order %s', order.name)
                continue

            # Process all order lines (filter out section lines)
            for line in lines.filtered(lambda l: l.product_id):
                try:
                    existing = line.analytic_distribution or {}

                    # Only add if not already present
                    if key not in existing:
                        new_dist = dict(existing)
                        new_dist[key] = 100.0
                        line.analytic_distribution = new_dist
                        _logger.debug(
                            'Warehouse analytic %s applied to POS order line %s (product: %s)',
                            analytic_account.name, line.id, line.product_id.name,
                        )
                except Exception as e:
                    _logger.warning(
                        'Error applying warehouse analytic to POS line %s: %s',
                        line.id, str(e)
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Apply warehouse analytic on POS order creation."""
        orders = super().create(vals_list)
        try:
            orders._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error applying warehouse analytic to POS order: %s', str(e))
        return orders

    def write(self, vals):
        """Re-apply warehouse analytic when order is modified."""
        result = super().write(vals)
        try:
            if 'lines_ids' in vals or any(k in vals for k in ('state', 'amount_total')):
                self._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error updating warehouse analytic on POS order: %s', str(e))
        return result

    def action_pos_order_paid(self):
        """
        Called when order is marked as paid.
        Re-apply analytic before payment to ensure correct distribution.
        """
        try:
            self._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error applying analytic on pos_order_paid: %s', str(e))
        return super().action_pos_order_paid()

    def action_pos_order_done(self):
        """
        Called when order is finalized.
        Final check to ensure analytics are applied.
        """
        try:
            self._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error applying analytic on pos_order_done: %s', str(e))
        return super().action_pos_order_done()


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    @api.model_create_multi
    def create(self, vals_list):
        """Apply warehouse analytic when POS order lines are created."""
        lines = super().create(vals_list)

        # Trigger analytic application on parent order
        try:
            for line in lines:
                if line.order_id:
                    line.order_id._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error applying analytic to new POS order line: %s', str(e))

        return lines

    def write(self, vals):
        """Re-apply analytic when POS order line is modified."""
        result = super().write(vals)

        try:
            # Re-apply if product or analytic distribution changed
            if any(k in vals for k in ('product_id', 'analytic_distribution', 'qty')):
                for line in self:
                    if line.order_id:
                        line.order_id._apply_warehouse_analytic_to_lines()
        except Exception as e:
            _logger.warning('Error updating analytic on POS order line: %s', str(e))

        return result

    @api.onchange('product_id')
    def _onchange_product_apply_warehouse_analytic(self):
        """
        Apply warehouse analytic when product is selected in a POS order line.
        This provides instant feedback in the POS interface.
        """
        try:
            if not self.order_id:
                return

            wh = _get_user_warehouse(self.env.user)

            # Also try session warehouse if user warehouse not found
            if not wh and self.order_id.session_id and self.order_id.session_id.config_id:
                location = self.order_id.session_id.config_id.stock_location_id
                if location and location.warehouse_id:
                    wh = location.warehouse_id

            if not wh or not wh.analytic_account_id:
                return

            key = str(wh.analytic_account_id.id)
            existing = self.analytic_distribution or {}

            if key not in existing:
                new_dist = dict(existing)
                new_dist[key] = 100.0
                self.analytic_distribution = new_dist
        except Exception as e:
            _logger.warning('Error in POS line onchange handler: %s', str(e))