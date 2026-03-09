from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_customer_id = fields.Many2one(
        'res.partner',
        string='POS Cash Customer',
        help='The master CASH CUSTOMER partner. All new POS customers will be added as contacts under this partner. Leave empty to use the standard create customer form.',
        store=True,   # ← CRITICAL: force Odoo to persist this field on the transient record
    )

    def set_values(self):
        _logger.info("=== set_values(): self.id=%s pos_cash_customer_id=%s", self.id, self.pos_cash_customer_id)
        super().set_values()
        # Re-read directly from DB in case ORM cache is stale
        if self.id:
            self.env.cr.execute(
                "SELECT pos_cash_customer_id FROM res_config_settings WHERE id = %s",
                (self.id,)
            )
            row = self.env.cr.fetchone()
            db_val = row[0] if row else None
            _logger.info("=== set_values(): RAW DB value = %s", db_val)
            partner_id = db_val or self.pos_cash_customer_id.id or 0
        else:
            partner_id = self.pos_cash_customer_id.id or 0

        _logger.info("=== set_values(): saving partner_id=%s", partner_id)
        self.env['ir.config_parameter'].sudo().set_param(
            'pos_cash_customer.cash_customer_id',
            str(partner_id) if partner_id else '0'
        )
        saved = self.env['ir.config_parameter'].sudo().get_param('pos_cash_customer.cash_customer_id')
        _logger.info("=== set_values(): confirmed ICP value = %s", saved)

    @api.model
    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param(
            'pos_cash_customer.cash_customer_id', '0'
        )
        _logger.info("=== get_values(): raw param='%s'", param)
        try:
            partner_id = int(param) if param else 0
        except (ValueError, TypeError):
            partner_id = 0
        if partner_id:
            exists = self.env['res.partner'].sudo().browse(partner_id).exists()
            if not exists:
                partner_id = 0
        res['pos_cash_customer_id'] = partner_id if partner_id else False
        _logger.info("=== get_values(): returning partner_id=%s", res['pos_cash_customer_id'])
        return res