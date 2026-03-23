import logging
import re
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    whatsapp_sent = fields.Boolean(string='WhatsApp Receipt Sent', default=False, copy=False)
    whatsapp_log_ids = fields.One2many('pos.whatsapp.log', 'pos_order_id', string='WhatsApp Logs')

    @api.model
    def send_whatsapp_receipt(self, order_id, phone_override=None):
        order = self.browse(order_id)
        if not order.exists():
            return {'success': False, 'message': _('Order not found.')}
        phone = phone_override or self._get_customer_phone(order)
        if not phone:
            return {'success': False, 'message': _('No phone number found for this customer.')}
        phone = self._normalize_phone(phone)
        if not phone:
            return {'success': False, 'message': _('Invalid phone number format.')}
        message = self._build_receipt_message(order)
        provider = self.env['ir.config_parameter'].sudo().get_param(
            'pos_whatsapp_receipt.provider', 'meta'
        )
        try:
            if provider == 'meta':
                self._send_via_meta(phone, message)
            elif provider == 'twilio':
                self._send_via_twilio(phone, message)
            else:
                return {'success': False, 'message': _('No WhatsApp provider configured.')}
            order.sudo().write({'whatsapp_sent': True})
            self._log_whatsapp(order, phone, message, provider, 'sent')
            _logger.info("WhatsApp receipt sent successfully to %s for order %s", phone, order.name)
            return {'success': True, 'message': _('Receipt sent to %s') % phone}
        except Exception as e:
            _logger.error("WhatsApp send failed for order %s: %s", order.name, str(e))
            self._log_whatsapp(order, phone, message, provider, 'failed', str(e))
            return {'success': False, 'message': str(e)}

    @api.model
    def sync_from_ui(self, orders):
        """Override sync_from_ui — this is the actual hook in Odoo 19 POS."""
        result = super().sync_from_ui(orders)
        auto_send = self.env['ir.config_parameter'].sudo().get_param(
            'pos_whatsapp_receipt.auto_send', 'True'
        )
        if auto_send not in ('True', '1', 'true'):
            return result
        try:
            order_ids = [o.get('id') for o in result.get('pos.order', []) if o.get('id')]
            for order_id in order_ids:
                order = self.browse(order_id)
                if order.exists() and order.state in ('paid', 'done', 'invoiced') and not order.whatsapp_sent:
                    phone = self._get_customer_phone(order)
                    if phone:
                        _logger.info("Auto-sending WhatsApp for order %s to %s", order.name, phone)
                        self.send_whatsapp_receipt(order_id)
                    else:
                        _logger.info("No phone number for order %s, skipping WhatsApp", order.name)
        except Exception as e:
            _logger.warning("WhatsApp auto-send error in sync_from_ui: %s", str(e))
        return result

    def action_pos_order_paid(self):
        """Keep this as fallback for backend-created orders."""
        res = super().action_pos_order_paid()
        auto_send = self.env['ir.config_parameter'].sudo().get_param(
            'pos_whatsapp_receipt.auto_send', 'True'
        )
        if auto_send in ('True', '1', 'true'):
            for order in self:
                if not order.whatsapp_sent:
                    phone = self._get_customer_phone(order)
                    if phone:
                        try:
                            self.send_whatsapp_receipt(order.id)
                        except Exception as e:
                            _logger.warning("WhatsApp send skipped for order %s: %s", order.name, e)
        return res

    def action_send_whatsapp_manual(self):
        self.ensure_one()
        result = self.send_whatsapp_receipt(self.id)
        if result['success']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('WhatsApp'),
                    'message': result['message'],
                    'type': 'success',
                    'sticky': False,
                },
            }
        else:
            raise UserError(result['message'])

    def _build_receipt_message(self, order):
        template = self.env['ir.config_parameter'].sudo().get_param(
            'pos_whatsapp_receipt.message_template', ''
        )
        if not template:
            template = (
                "Hello {customer_name}!\n\nThank you for shopping with us.\n\n"
                "Receipt: {order_ref}\nDate: {date}\n\n{order_lines}\n"
                "-----------------\nTotal: {currency} {total}\n\nSee you again!"
            )
        lines = []
        for line in order.lines:
            qty = int(line.qty) if line.qty == int(line.qty) else line.qty
            lines.append(
                f"  {line.product_id.name} x{qty}  "
                f"{line.currency_id.symbol}{line.price_subtotal_incl:.2f}"
            )
        customer_name = order.partner_id.name if order.partner_id else "Valued Customer"
        currency_symbol = order.currency_id.symbol if order.currency_id else ""
        message = template.format(
            customer_name=customer_name,
            order_ref=order.name or '',
            date=fields.Datetime.context_timestamp(
                self, order.date_order
            ).strftime('%d %b %Y %I:%M %p') if order.date_order else '',
            order_lines="\n".join(lines) if lines else "(no items)",
            currency=currency_symbol,
            total=f"{order.amount_total:.2f}",
            company_name=order.company_id.name or '',
        )
        return message

    def _send_via_meta(self, phone, message):
        params = self.env['ir.config_parameter'].sudo()
        token = params.get_param('pos_whatsapp_receipt.meta_token')
        phone_id = params.get_param('pos_whatsapp_receipt.meta_phone_id')
        if not token or not phone_id:
            raise UserError(_('Meta WhatsApp API credentials are not configured.'))
        url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message},
        }
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code not in (200, 201):
            raise UserError(_('Meta API error %s: %s') % (response.status_code, response.text))

    def _send_via_twilio(self, phone, message):
        params = self.env['ir.config_parameter'].sudo()
        sid = params.get_param('pos_whatsapp_receipt.twilio_sid')
        token = params.get_param('pos_whatsapp_receipt.twilio_token')
        from_num = params.get_param('pos_whatsapp_receipt.twilio_from')
        if not sid or not token or not from_num:
            raise UserError(_('Twilio WhatsApp credentials are not configured.'))
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        data = {'From': from_num, 'To': f'whatsapp:{phone}', 'Body': message}
        response = requests.post(url, data=data, auth=(sid, token), timeout=15)
        if response.status_code not in (200, 201):
            raise UserError(_('Twilio API error %s: %s') % (response.status_code, response.text))

    def _get_customer_phone(self, order):
        partner = order.partner_id
        if not partner:
            return None
        phone = getattr(partner, 'mobile', None) or getattr(partner, 'phone', None)
        if not phone:
            full_partner = self.env['res.partner'].sudo().browse(partner.id)
            phone = getattr(full_partner, 'mobile', None) or getattr(full_partner, 'phone', None)
        return phone

    @staticmethod
    def _normalize_phone(phone):
        digits = re.sub(r'\D', '', phone)
        if not digits:
            return None
        if not phone.strip().startswith('+'):
            if len(digits) == 10:
                digits = '91' + digits
        return digits

    def _log_whatsapp(self, order, phone, message, provider, state, error=None):
        self.env['pos.whatsapp.log'].sudo().create({
            'pos_order_id': order.id,
            'partner_id': order.partner_id.id if order.partner_id else False,
            'phone': phone,
            'message': message,
            'provider': provider,
            'state': state,
            'error_message': error,
        })
