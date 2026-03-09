from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_cash_customer_id = fields.Many2one(
        'res.partner',
        string='POS Cash Customer',
        help='The master CASH CUSTOMER partner. All new POS customers will be added as contacts under this partner. Leave empty to use the standard create customer form.',
    )

    def set_values(self):
        super().set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        partner_id = self.pos_cash_customer_id.id
        if partner_id:
            ICP.set_param('pos_cash_customer.cash_customer_id', str(partner_id))
        else:
            ICP.set_param('pos_cash_customer.cash_customer_id', '0')

    @api.model
    def get_values(self):
        res = super().get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        param = ICP.get_param('pos_cash_customer.cash_customer_id', '0')
        try:
            partner_id = int(param)
        except (ValueError, TypeError):
            partner_id = 0

        # Verify the partner actually exists before returning it
        if partner_id:
            exists = self.env['res.partner'].sudo().search(
                [('id', '=', partner_id)], limit=1
            )
            if not exists:
                partner_id = 0

        res['pos_cash_customer_id'] = partner_id if partner_id else False
        return res