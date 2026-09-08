# from odoo import models, fields, api
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     allowed_warehouse_domain = fields.Many2many(
#         'stock.warehouse',
#         string='Allowed Warehouse Domain',
#         compute='_compute_allowed_warehouse_domain',
#     )
#
#     allowed_location_domain = fields.Many2many(
#         'stock.location',
#         string='Allowed Location Domain',
#         compute='_compute_allowed_location_domain',
#     )
#
#     @api.depends_context('uid')
#     def _compute_allowed_warehouse_domain(self):
#         user = self.env.user
#         if user.allowed_warehouse_ids:
#             allowed = user.allowed_warehouse_ids
#         else:
#             allowed = self.env['stock.warehouse'].search([])
#         for record in self:
#             record.allowed_warehouse_domain = allowed
#
#     @api.depends_context('uid')
#     def _compute_allowed_location_domain(self):
#         user = self.env.user
#         if user.allowed_warehouse_ids:
#             # Get all locations that belong to allowed warehouses
#             # Each warehouse has a view_location_id which is the parent of all its locations
#             wh_location_ids = user.allowed_warehouse_ids.mapped('view_location_id').ids
#             allowed_locations = self.env['stock.location'].search([
#                 ('location_id', 'child_of', wh_location_ids),
#             ])
#             # Also include virtual locations like Customers, Suppliers, Inventory Loss
#             virtual_locations = self.env['stock.location'].search([
#                 ('usage', 'in', ['customer', 'supplier', 'inventory', 'production']),
#             ])
#             allowed = allowed_locations | virtual_locations
#         else:
#             allowed = self.env['stock.location'].search([])
#         for record in self:
#             record.allowed_location_domain = allowed
from odoo import models, fields, api
from .utils import get_request_cache, cache_key


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    allowed_warehouse_domain = fields.Many2many(
        'stock.warehouse',
        string='Allowed Warehouse Domain',
        compute='_compute_allowed_warehouse_domain',
    )

    allowed_location_domain = fields.Many2many(
        'stock.location',
        string='Allowed Location Domain',
        compute='_compute_allowed_location_domain',
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
    def _compute_allowed_location_domain(self):
        """
        OPTIMIZATION: this ran two full stock.location searches every time
        this compute fired — which happens on every list/kanban/form render
        of stock.picking, not just once. Cached per-request so it now runs
        those searches at most once per request no matter how many pickings
        are on screen.
        """
        user = self.env.user

        if user.allowed_warehouse_ids:
            cache = get_request_cache(self.env.cr)
            key = cache_key('allowed_locations', user.id)
            if key in cache:
                allowed = cache[key]
            else:
                wh_location_ids = user.allowed_warehouse_ids.mapped('view_location_id').ids
                allowed_locations = self.env['stock.location'].search([
                    ('location_id', 'child_of', wh_location_ids),
                ])
                virtual_locations = self.env['stock.location'].search([
                    ('usage', 'in', ['customer', 'supplier', 'inventory', 'production']),
                ])
                allowed = allowed_locations | virtual_locations
                cache[key] = allowed
        else:
            allowed = self.env['stock.location'].search([])

        for record in self:
            record.allowed_location_domain = allowed