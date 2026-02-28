from odoo import models, fields, api


class PurchaseOrder(models.Model):
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
