from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_customer_id = fields.Many2one(
        'res.partner',
        string='POS Cash Customer',
        help='The master CASH CUSTOMER partner. All new POS customers will be added as contacts under this partner. Leave empty to use the standard create customer form.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """In Odoo 19, settings creates a fresh transient record on every Save.
        The field value is in vals_list — capture it here immediately."""
        records = super().create(vals_list)
        ICP = self.env['ir.config_parameter'].sudo()
        for rec, vals in zip(records, vals_list):
            raw = vals.get('pos_cash_customer_id')
            _logger.info("=== create(): pos_cash_customer_id in vals = %s", raw)
            if raw and isinstance(raw, int):
                ICP.set_param('pos_cash_customer.cash_customer_id', str(raw))
                _logger.info("=== create(): SAVED partner_id=%s to ICP", raw)
            elif 'pos_cash_customer_id' in vals and not raw:
                # Explicitly cleared by user
                ICP.set_param('pos_cash_customer.cash_customer_id', '0')
                _logger.info("=== create(): CLEARED partner_id in ICP")
        return records

    def set_values(self):
        """Fallback for any non-create path."""
        super().set_values()
        partner_id = self.pos_cash_customer_id.id
        _logger.info("=== set_values(): partner_id=%s", partner_id)
        if partner_id:
            self.env['ir.config_parameter'].sudo().set_param(
                'pos_cash_customer.cash_customer_id', str(partner_id)
            )

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