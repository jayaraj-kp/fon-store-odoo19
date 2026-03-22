from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # WhatsApp Provider Selection
    pos_whatsapp_provider = fields.Selection(
        selection=[
            ('twilio', 'Twilio WhatsApp API'),
            ('meta', 'Meta WhatsApp Business Cloud API'),
        ],
        string='WhatsApp Provider',
        config_parameter='pos_whatsapp_receipt.provider',
        default='meta',
    )

    # Auto-send toggle
    pos_whatsapp_auto_send = fields.Boolean(
        string='Auto-send Receipt via WhatsApp',
        config_parameter='pos_whatsapp_receipt.auto_send',
        default=True,
        help='Automatically send receipt to customer WhatsApp after POS transaction',
    )

    # ── Meta (WhatsApp Business Cloud API) ──
    pos_whatsapp_meta_token = fields.Char(
        string='Meta API Access Token',
        config_parameter='pos_whatsapp_receipt.meta_token',
    )
    pos_whatsapp_meta_phone_id = fields.Char(
        string='Meta Phone Number ID',
        config_parameter='pos_whatsapp_receipt.meta_phone_id',
        help='The Phone Number ID from your Meta WhatsApp Business account',
    )

    # ── Twilio ──
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
        help='Format: whatsapp:+14155238886',
    )

    # ── Receipt Message Template ──
    pos_whatsapp_message_template = fields.Text(
        string='Receipt Message Template',
        config_parameter='pos_whatsapp_receipt.message_template',
        default="""Hello {customer_name}! 🛍️

Thank you for shopping with us.

🧾 *Receipt: {order_ref}*
📅 Date: {date}

{order_lines}
─────────────────
💰 *Total: {currency} {total}*

We appreciate your business! See you again. 😊""",
        help='Available placeholders: {customer_name}, {order_ref}, {date}, {order_lines}, {currency}, {total}, {company_name}',
    )
