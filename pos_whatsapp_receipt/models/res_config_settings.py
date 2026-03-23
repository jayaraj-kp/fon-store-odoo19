from odoo import api, fields, models

DEFAULT_TEMPLATE = """Hello {customer_name}! 

Thank you for shopping with us.

*Receipt: {order_ref}*
Date: {date}

{order_lines}
-----------------
*Total: {currency} {total}*

We appreciate your business!"""


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_whatsapp_provider = fields.Selection(
        selection=[
            ('twilio', 'Twilio WhatsApp API'),
            ('meta', 'Meta WhatsApp Business Cloud API'),
        ],
        string='WhatsApp Provider',
        config_parameter='pos_whatsapp_receipt.provider',
        default='meta',
    )
    pos_whatsapp_auto_send = fields.Boolean(
        string='Auto-send Receipt via WhatsApp',
        config_parameter='pos_whatsapp_receipt.auto_send',
        default=True,
    )
    pos_whatsapp_meta_token = fields.Char(
        string='Meta API Access Token',
        config_parameter='pos_whatsapp_receipt.meta_token',
    )
    pos_whatsapp_meta_phone_id = fields.Char(
        string='Meta Phone Number ID',
        config_parameter='pos_whatsapp_receipt.meta_phone_id',
    )
    pos_whatsapp_twilio_sid = fields.Char(
        string='Twilio Account SID',
        config_parameter='pos_whatsapp_receipt.twilio_sid',
    )
    pos_whatsapp_twilio_token = fields.Char(
        string='Twilio Auth Token',
        config_parameter='pos_whatsapp_receipt.twilio_token',
    )
    pos_whatsapp_twilio_from = fields.Char(
        string='Twilio WhatsApp From Number',
        config_parameter='pos_whatsapp_receipt.twilio_from',
    )
    # Text field: manually handled via get_param/set_param
    pos_whatsapp_message_template = fields.Text(
        string='Receipt Message Template',
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        res['pos_whatsapp_message_template'] = (
            self.env['ir.config_parameter'].sudo().get_param(
                'pos_whatsapp_receipt.message_template', DEFAULT_TEMPLATE
            )
        )
        return res

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'pos_whatsapp_receipt.message_template',
            self.pos_whatsapp_message_template or DEFAULT_TEMPLATE,
        )
