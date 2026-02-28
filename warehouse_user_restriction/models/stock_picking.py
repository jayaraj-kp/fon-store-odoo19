from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    allowed_warehouse_domain = fields.Many2many(
        'stock.warehouse',
        'stock_picking_allowed_wh_rel',
        'picking_id',
        'warehouse_id',
        string='Allowed Warehouse Domain',
        compute='_compute_allowed_warehouse_domain',
    )

    allowed_location_ids = fields.Many2many(
        'stock.location',
        string='Allowed Locations Domain',
        compute='_compute_allowed_location_ids',
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

    @api.depends_context('uid')
    def _compute_allowed_location_ids(self):
        user = self.env.user
        if user.allowed_warehouse_ids:
            # Get all locations that belong to the allowed warehouses
            # Each warehouse has a view_location_id which is the parent of all its locations
            allowed_location_ids = []
            for wh in user.allowed_warehouse_ids:
                locations = self.env['stock.location'].search([
                    ('complete_name', 'like', wh.code + '/'),
                ])
                allowed_location_ids += locations.ids
                # Also include the warehouse root location
                if wh.lot_stock_id:
                    allowed_location_ids.append(wh.lot_stock_id.id)
                if wh.view_location_id:
                    child_locs = self.env['stock.location'].search([
                        ('id', 'child_of', wh.view_location_id.id)
                    ])
                    allowed_location_ids += child_locs.ids
            # Always include virtual locations (Customers, Vendors, etc.)
            virtual_locations = self.env['stock.location'].search([
                ('usage', 'in', ['customer', 'supplier', 'inventory', 'production', 'transit']),
            ])
            allowed_location_ids += virtual_locations.ids
            allowed_locs = self.env['stock.location'].browse(list(set(allowed_location_ids)))
        else:
            allowed_locs = self.env['stock.location'].search([])
        for record in self:
            record.allowed_location_ids = allowed_locs
