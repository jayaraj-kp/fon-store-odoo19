from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Filter purchase orders to only show those for allowed warehouses.

        This is the read restriction for lists, searches and dropdowns.
        (The ir.rule for purchase.order no longer restricts 'read', so
        internal flows such as POS payment sync can read related POs.)

        POs with no warehouse on their operation type stay visible, matching
        the behaviour of the record rule.
        """
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            domain = list(domain) + [
                '|',
                ('picking_type_id.warehouse_id', 'in', user.allowed_warehouse_ids.ids),
                ('picking_type_id.warehouse_id', '=', False),
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