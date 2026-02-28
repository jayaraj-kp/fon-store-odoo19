from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allowed_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Linked Warehouse',
        help='Link this POS to a warehouse for user restriction purposes.',
        # Exclude from POS frontend loading to prevent IndexedDB errors
        export_string_translation=False,
    )

    def _get_pos_ui_pos_config(self, params):
        """Override to exclude allowed_warehouse_id from POS UI data."""
        result = super()._get_pos_ui_pos_config(params)
        # Remove the field from POS data to prevent IndexedDB TypeError
        for config in result:
            config.pop('allowed_warehouse_id', None)
        return result

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Filter POS configs to only show those linked to allowed warehouses."""
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            domain = list(domain) + [
                ('allowed_warehouse_id', 'in', allowed_wh_ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            domain = list(domain) + [
                ('config_id.allowed_warehouse_id', 'in', allowed_wh_ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
