# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _is_cost_block_active(self):
        """Check if the cost price block feature is enabled."""
        IrConfig = self.env['ir.config_parameter'].sudo()
        return IrConfig.get_param('sale_cost_price_block.block_sale_below_cost', False)

    def _is_manager_override_allowed(self):
        """Check if the current user is a Sales Manager and override is allowed."""
        IrConfig = self.env['ir.config_parameter'].sudo()
        allow_override = IrConfig.get_param(
            'sale_cost_price_block.allow_manager_override', False)
        if allow_override:
            return self.env.user.has_group('sales_team.group_sale_manager')
        return False

    def _check_lines_below_cost(self):
        """
        Returns a list of dicts describing any order lines priced below cost.
        Each dict: {product_name, sale_price, cost_price, currency}
        """
        violations = []
        for line in self.order_line:
            if not line.product_id:
                continue
            # Get product cost in company currency
            cost_price = line.product_id.standard_price
            if cost_price <= 0:
                # No cost defined — skip check
                continue
            # Compare unit price (already in order's currency) to cost price
            # Convert cost to order currency if different
            cost_in_order_currency = cost_price
            if self.currency_id != self.company_id.currency_id:
                cost_in_order_currency = self.company_id.currency_id._convert(
                    cost_price,
                    self.currency_id,
                    self.company_id,
                    self.date_order or fields.Date.today(),
                )
            if line.price_unit < cost_in_order_currency:
                violations.append({
                    'product_name': line.product_id.display_name,
                    'sale_price': line.price_unit,
                    'cost_price': cost_in_order_currency,
                    'currency': self.currency_id.symbol or self.currency_id.name,
                })
        return violations

    def action_confirm(self):
        """Override to block confirmation if any line is below cost."""
        if self._is_cost_block_active() and not self._is_manager_override_allowed():
            for order in self:
                violations = order._check_lines_below_cost()
                if violations:
                    lines_info = '\n'.join(
                        _('• %s: Sale Price %s%.2f < Cost Price %s%.2f') % (
                            v['product_name'],
                            v['currency'], v['sale_price'],
                            v['currency'], v['cost_price'],
                        )
                        for v in violations
                    )
                    raise UserError(
                        _('⚠️ Cannot Confirm Order — Price Below Cost!\n\n'
                          'The following product(s) are priced below their cost price:\n\n'
                          '%s\n\n'
                          'Please adjust the unit prices before confirming the order.')
                        % lines_info
                    )
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    price_below_cost = fields.Boolean(
        string='Price Below Cost',
        compute='_compute_price_below_cost',
        store=False,
    )
    cost_price = fields.Float(
        string='Cost Price',
        compute='_compute_price_below_cost',
        store=False,
        digits='Product Price',
    )

    @api.depends('product_id', 'price_unit', 'order_id.currency_id',
                 'order_id.company_id', 'order_id.date_order')
    def _compute_price_below_cost(self):
        for line in self:
            cost = 0.0
            below = False
            if line.product_id and line.product_id.standard_price > 0:
                cost = line.product_id.standard_price
                order = line.order_id
                # Convert cost to order currency if needed
                if order.currency_id and order.company_id.currency_id \
                        and order.currency_id != order.company_id.currency_id:
                    cost = order.company_id.currency_id._convert(
                        cost,
                        order.currency_id,
                        order.company_id,
                        order.date_order or fields.Date.today(),
                    )
                below = line.price_unit < cost
            line.price_below_cost = below
            line.cost_price = cost

    @api.constrains('price_unit', 'product_id')
    def _constrains_price_above_cost(self):
        """Real-time validation when saving lines."""
        IrConfig = self.env['ir.config_parameter'].sudo()
        if not IrConfig.get_param('sale_cost_price_block.block_sale_below_cost', False):
            return
        for line in self:
            if line.price_below_cost:
                # Check manager override
                allow_override = IrConfig.get_param(
                    'sale_cost_price_block.allow_manager_override', False)
                if allow_override and self.env.user.has_group(
                        'sales_team.group_sale_manager'):
                    continue
                raise ValidationError(
                    _('⚠️ Price Below Cost!\n\n'
                      'Product: %s\n'
                      'Sale Price: %.2f\n'
                      'Cost Price: %.2f\n\n'
                      'The unit price cannot be set below the product cost price.')
                    % (line.product_id.display_name,
                       line.price_unit,
                       line.cost_price)
                )
