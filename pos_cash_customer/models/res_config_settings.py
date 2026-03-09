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

    def create(self, vals_list):
        """In Odoo 19, settings uses create() not write() — the transient record
        is created fresh each time Save is clicked."""
        _logger.info("=== POS CASH CUSTOMER: create() CALLED, vals_list=%s", vals_list)
        records = super().create(vals_list)
        for rec, vals in zip(records, vals_list if isinstance(vals_list, list) else [vals_list]):
            raw = vals.get('pos_cash_customer_id')
            _logger.info("=== create(): raw pos_cash_customer_id in vals = %s", raw)
            if raw and isinstance(raw, int):
                ICP = self.env['ir.config_parameter'].sudo()
                ICP.set_param('pos_cash_customer.cash_customer_id', str(raw))
                saved = ICP.get_param('pos_cash_customer.cash_customer_id')
                _logger.info("=== create(): saved to ICP = %s", saved)
        return records

    def write(self, vals):
        _logger.info("=== POS CASH CUSTOMER: write() CALLED, vals=%s", vals)
        result = super().write(vals)
        raw = vals.get('pos_cash_customer_id')
        _logger.info("=== write(): raw pos_cash_customer_id in vals = %s", raw)
        if raw and isinstance(raw, int):
            ICP = self.env['ir.config_parameter'].sudo()
            ICP.set_param('pos_cash_customer.cash_customer_id', str(raw))
            saved = ICP.get_param('pos_cash_customer.cash_customer_id')
            _logger.info("=== write(): saved to ICP = %s", saved)
        return result

    def set_values(self):
        _logger.info("=== POS CASH CUSTOMER: set_values() CALLED ===")
        _logger.info("=== pos_cash_customer_id.id at set_values: %s", self.pos_cash_customer_id.id)
        super().set_values()
        partner_id = self.pos_cash_customer_id.id
        if partner_id:
            ICP = self.env['ir.config_parameter'].sudo()
            ICP.set_param('pos_cash_customer.cash_customer_id', str(partner_id))
            _logger.info("=== set_values(): saved partner_id=%s", partner_id)

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        param = ICP.get_param('pos_cash_customer.cash_customer_id', '0')
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

    @api.model
    def execute(self):
        """Override execute to log what self contains at execution time."""
        _logger.info("=== POS CASH CUSTOMER: execute() CALLED ===")
        _logger.info("=== execute(): self.ids=%s", self.ids)
        _logger.info("=== execute(): pos_cash_customer_id=%s", self.pos_cash_customer_id)
        _logger.info("=== execute(): pos_cash_customer_id.id=%s", self.pos_cash_customer_id.id)
        # Read directly from DB to see what was actually stored
        if self.ids:
            raw_db = self.env.cr.execute(
                "SELECT pos_cash_customer_id FROM res_config_settings WHERE id = %s",
                (self.ids[0],)
            )
            row = self.env.cr.fetchone()
            _logger.info("=== execute(): RAW DB value for pos_cash_customer_id = %s", row)
        return super().execute()