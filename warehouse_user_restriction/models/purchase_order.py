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
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            domain = list(domain) + [
                ('picking_type_id.warehouse_id', 'in', allowed_wh_ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_warehouse_check(self):
        """Filter the Deliver To dropdown to only allowed warehouses."""
        user = self.env.user
        if user.allowed_warehouse_ids:
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            return {
                'domain': {
                    'picking_type_id': [
                        ('warehouse_id', 'in', allowed_wh_ids),
                        ('code', '=', 'incoming'),
                    ]
                }
            }


class PurchaseOrderInheritView(models.Model):
    """Separate model to handle the view domain injection via _get_default."""
    _inherit = 'purchase.order'

    allowed_picking_type_domain = fields.Many2many(
        'stock.picking.type',
        string='Allowed Picking Type Domain',
        compute='_compute_allowed_picking_type_domain',
    )

    @api.depends_context('uid')
    def _compute_allowed_picking_type_domain(self):
        user = self.env.user
        if user.allowed_warehouse_ids:
            allowed = self.env['stock.picking.type'].search([
                ('warehouse_id', 'in', user.allowed_warehouse_ids.ids),
                ('code', '=', 'incoming'),
            ])
        else:
            allowed = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
            ])
        for record in self:
            record.allowed_picking_type_domain = allowed

    def _get_default_picking_type_id_domain(self):
        user = self.env.user
        if user.allowed_warehouse_ids:
            return [
                ('warehouse_id', 'in', user.allowed_warehouse_ids.ids),
                ('code', '=', 'incoming'),
            ]
        return [('code', '=', 'incoming')]
