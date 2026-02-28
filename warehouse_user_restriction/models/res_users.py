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

    default_customer_tag_ids = fields.Many2many(
        'res.partner.category',
        'res_users_partner_category_rel',
        'user_id',
        'category_id',
        string='Default Customer Tags',
        help='These tags will be automatically applied to any new customer '
             'created by this user (in POS, Contacts, or anywhere).',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'allowed_warehouse_ids',
            'default_customer_tag_ids',
        ]

    def _load_pos_data_fields(self, config_id):
        """Exclude our custom Many2many fields from POS data loading.
        These fields reference models not loaded in POS and cause IndexedDB crash."""
        fields = super()._load_pos_data_fields(config_id)
        # Remove our custom fields from POS loading
        fields_to_remove = ['allowed_warehouse_ids', 'default_customer_tag_ids']
        return [f for f in fields if f not in fields_to_remove]
