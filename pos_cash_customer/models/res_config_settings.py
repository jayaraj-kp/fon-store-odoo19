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

    def set_values(self):
        _logger.info("=== POS CASH CUSTOMER: set_values() CALLED ===")
        _logger.info("=== pos_cash_customer_id value: %s", self.pos_cash_customer_id)
        _logger.info("=== pos_cash_customer_id.id: %s", self.pos_cash_customer_id.id)
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        partner_id = self.pos_cash_customer_id.id
        _logger.info("=== Saving partner_id to ir.config_parameter: %s", partner_id)
        ICP.set_param('pos_cash_customer.cash_customer_id', str(partner_id) if partner_id else '0')
        # Read it back immediately to confirm it saved
        saved = ICP.get_param('pos_cash_customer.cash_customer_id')
        _logger.info("=== Value read back from ir.config_parameter: %s", saved)

    @api.model
    def get_values(self):
        _logger.info("=== POS CASH CUSTOMER: get_values() CALLED ===")
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        param = ICP.get_param('pos_cash_customer.cash_customer_id', '0')
        _logger.info("=== Raw param from ir.config_parameter: '%s'", param)
        try:
            partner_id = int(param) if param else 0
        except (ValueError, TypeError):
            partner_id = 0
        _logger.info("=== Parsed partner_id: %s", partner_id)

        if partner_id:
            exists = self.env['res.partner'].sudo().browse(partner_id).exists()
            _logger.info("=== Partner exists in DB: %s", bool(exists))
            if not exists:
                partner_id = 0

        res['pos_cash_customer_id'] = partner_id if partner_id else False
        _logger.info("=== Returning pos_cash_customer_id as: %s", res['pos_cash_customer_id'])
        return res