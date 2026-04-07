# -*- coding: utf-8 -*-
import json
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _order_fields(self, ui_order):
        """Validate cost price before processing POS order from the frontend."""
        IrConfig = self.env['ir.config_parameter'].sudo()
        if IrConfig.get_param('sale_cost_price_block.block_sale_below_cost', False):
            allow_override = IrConfig.get_param(
                'sale_cost_price_block.allow_manager_override', False)
            is_manager = self.env.user.has_group('sales_team.group_sale_manager')
            if not (allow_override and is_manager):
                violations = self._check_pos_lines_below_cost(ui_order)
                if violations:
                    lines_info = ', '.join(
                        '%s (sale: %.2f < cost: %.2f)' % (
                            v['product_name'], v['sale_price'], v['cost_price'])
                        for v in violations
                    )
                    raise UserError(
                        _('⚠️ Cannot process POS order — price below cost!\n\n'
                          'Products: %s\n\n'
                          'Please adjust prices before payment.') % lines_info
                    )
        return super()._order_fields(ui_order)

    @api.model
    def _check_pos_lines_below_cost(self, ui_order):
        """Check each order line in a POS UI order dict for below-cost prices."""
        violations = []
        lines = ui_order.get('lines', [])
        for line_data in lines:
            # line_data is [0, 0, {...}] (Many2many command format)
            if isinstance(line_data, (list, tuple)) and len(line_data) >= 3:
                line = line_data[2]
            elif isinstance(line_data, dict):
                line = line_data
            else:
                continue

            product_id = line.get('product_id')
            price_unit = line.get('price_unit', 0.0)

            if not product_id:
                continue

            product = self.env['product.product'].browse(product_id)
            if not product.exists():
                continue

            cost_price = product.standard_price
            if cost_price <= 0:
                continue

            if price_unit < cost_price:
                violations.append({
                    'product_name': product.display_name,
                    'sale_price': price_unit,
                    'cost_price': cost_price,
                })
        return violations


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        """Ensure standard_price is sent to POS frontend."""
        result = super()._loader_params_product_product()
        if 'standard_price' not in result['search_params']['fields']:
            result['search_params']['fields'].append('standard_price')
        return result

    def get_pos_ui_product_product_by_params(self, custom_search_params):
        """Ensure standard_price is included in dynamic product loads."""
        result = super().get_pos_ui_product_product_by_params(custom_search_params)
        return result

    def _get_pos_ui_res_config_settings(self):
        """Inject cost-block config into POS session data."""
        result = super()._get_pos_ui_res_config_settings() \
            if hasattr(super(), '_get_pos_ui_res_config_settings') else {}
        IrConfig = self.env['ir.config_parameter'].sudo()
        result['block_sale_below_cost'] = IrConfig.get_param(
            'sale_cost_price_block.block_sale_below_cost', False)
        result['allow_manager_override'] = IrConfig.get_param(
            'sale_cost_price_block.allow_manager_override', False)
        result['current_user_is_manager'] = self.env.user.has_group(
            'sales_team.group_sale_manager')
        return result

    def load_pos_data(self):
        """Inject custom settings into _server_data for frontend use."""
        data = super().load_pos_data()
        IrConfig = self.env['ir.config_parameter'].sudo()
        if '_server_data' not in data:
            data['_server_data'] = {}
        data['_server_data']['block_sale_below_cost'] = bool(
            IrConfig.get_param('sale_cost_price_block.block_sale_below_cost', False))
        data['_server_data']['allow_manager_override'] = bool(
            IrConfig.get_param('sale_cost_price_block.allow_manager_override', False))
        data['_server_data']['current_user_is_manager'] = self.env.user.has_group(
            'sales_team.group_sale_manager')
        return data
