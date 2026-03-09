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

    def write(self, vals):
        """Intercept write() — this is called by web_save BEFORE execute/set_values.
        In Odoo 19, the transient record is written first, then execute() is called.
        We capture the partner_id here while the value is still in vals or on self.
        """
        _logger.info("=== POS CASH CUSTOMER: write() CALLED, vals=%s", vals)
        result = super().write(vals)

        # After super().write(), the value is now on self
        partner_id = self.pos_cash_customer_id.id
        _logger.info("=== write(): pos_cash_customer_id.id after super = %s", partner_id)

        ICP = self.env['ir.config_parameter'].sudo()
        if 'pos_cash_customer_id' in vals:
            # vals contains the raw integer ID for Many2one fields
            raw = vals.get('pos_cash_customer_id')
            _logger.info("=== write(): raw value from vals = %s", raw)
            # Many2one in vals can be an int or False
            pid = raw if isinstance(raw, int) and raw else (partner_id or 0)
            _logger.info("=== write(): saving pid=%s to ir.config_parameter", pid)
            ICP.set_param('pos_cash_customer.cash_customer_id', str(pid) if pid else '0')
            saved = ICP.get_param('pos_cash_customer.cash_customer_id')
            _logger.info("=== write(): confirmed saved value = %s", saved)

        return result

    def set_values(self):
        _logger.info("=== POS CASH CUSTOMER: set_values() CALLED ===")
        _logger.info("=== pos_cash_customer_id.id at set_values: %s", self.pos_cash_customer_id.id)
        super().set_values()
        # set_values is a fallback — value may already be saved by write()
        partner_id = self.pos_cash_customer_id.id
        if partner_id:
            ICP = self.env['ir.config_parameter'].sudo()
            ICP.set_param('pos_cash_customer.cash_customer_id', str(partner_id))
            _logger.info("=== set_values(): saved partner_id=%s", partner_id)

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

        if partner_id:
            exists = self.env['res.partner'].sudo().browse(partner_id).exists()
            _logger.info("=== Partner exists in DB: %s", bool(exists))
            if not exists:
                partner_id = 0

        res['pos_cash_customer_id'] = partner_id if partner_id else False
        _logger.info("=== Returning pos_cash_customer_id as: %s", res['pos_cash_customer_id'])
        return res