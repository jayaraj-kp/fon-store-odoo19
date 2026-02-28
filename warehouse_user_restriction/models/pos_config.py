from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            # Get warehouse names to match against POS config names
            wh_names = user.allowed_warehouse_ids.mapped('name')
            # Get POS config ids that match allowed warehouses by checking
            # their picking types' warehouse
            allowed_config_ids = []
            all_configs = self.env['pos.config'].sudo().search([])
            for config in all_configs:
                # Check via picking type warehouse
                if config.picking_type_id and config.picking_type_id.warehouse_id:
                    if config.picking_type_id.warehouse_id.id in user.allowed_warehouse_ids.ids:
                        allowed_config_ids.append(config.id)
                else:
                    allowed_config_ids.append(config.id)
            if allowed_config_ids:
                domain = list(domain) + [('id', 'in', allowed_config_ids)]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_config_ids = []
            all_configs = self.env['pos.config'].sudo().search([])
            for config in all_configs:
                if config.picking_type_id and config.picking_type_id.warehouse_id:
                    if config.picking_type_id.warehouse_id.id in user.allowed_warehouse_ids.ids:
                        allowed_config_ids.append(config.id)
                else:
                    allowed_config_ids.append(config.id)
            if allowed_config_ids:
                domain = list(domain) + [('config_id', 'in', allowed_config_ids)]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
