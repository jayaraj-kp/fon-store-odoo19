import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'res_users_stock_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Allowed Warehouses',
    )

    default_customer_tag_ids = fields.Many2many(
        'res.partner.category',
        'res_users_partner_category_rel',
        'user_id',
        'category_id',
        string='Default Customer Tags',
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'allowed_warehouse_ids',
            'default_customer_tag_ids',
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        result = super()._load_pos_data_fields(config)
        _logger.info("WHR_DEBUG _load_pos_data_fields called, original fields: %s", result)
        safe = ['id', 'name', 'partner_id', 'all_group_ids']
        _logger.info("WHR_DEBUG returning safe fields: %s", safe)
        return safe
