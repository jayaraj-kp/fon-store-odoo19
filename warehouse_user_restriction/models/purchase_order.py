from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Filter purchase orders to only show those for allowed warehouses."""
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            domain = list(domain) + [
                ('picking_type_id.warehouse_id', 'in', user.allowed_warehouse_ids.ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.model
    def default_get(self, fields_list):
        """Set default Deliver To based on user's allowed warehouse."""
        res = super().default_get(fields_list)
        user = self.env.user
        if 'picking_type_id' in fields_list and user.allowed_warehouse_ids:
            picking_type = self.env['stock.picking.type'].search([
                ('warehouse_id', 'in', user.allowed_warehouse_ids.ids),
                ('code', '=', 'incoming'),
            ], limit=1)
            if picking_type:
                res['picking_type_id'] = picking_type.id
        return res
