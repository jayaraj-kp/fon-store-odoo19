from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'res_users_stock_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Allowed Warehouses',
        help='If set, this user can only perform transactions in these warehouses. '
             'Leave empty to allow access to all warehouses.',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['allowed_warehouse_ids']
