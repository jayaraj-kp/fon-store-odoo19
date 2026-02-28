from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    allowed_warehouse_domain = fields.Many2many(
        'stock.warehouse',
        string='Allowed Warehouse Domain',
        compute='_compute_allowed_warehouse_domain',
    )

    @api.depends_context('uid')
    def _compute_allowed_warehouse_domain(self):
        user = self.env.user
        if user.allowed_warehouse_ids:
            allowed = user.allowed_warehouse_ids
        else:
            allowed = self.env['stock.warehouse'].search([])
        for record in self:
            record.allowed_warehouse_domain = allowed
