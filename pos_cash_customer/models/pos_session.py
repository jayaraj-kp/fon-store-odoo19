from odoo import models, fields


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Declare as a real field on pos.config so Odoo 19's ORM-based
    # POS data loader picks it up automatically — no manual injection needed.
    cash_customer_id = fields.Many2one(
        'res.partner',
        string='Cash Customer',
        compute='_compute_cash_customer_id',
    )

    def _compute_cash_customer_id(self):
        cash_customer_id = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'pos_cash_customer.cash_customer_id', 0
            )
        )
        for config in self:
            config.cash_customer_id = cash_customer_id or False