from odoo import fields, models


class PosWhatsappLog(models.Model):
    _name = 'pos.whatsapp.log'
    _description = 'POS WhatsApp Message Log'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False,
                       readonly=True, default='New')
    pos_order_id = fields.Many2one('pos.order', string='POS Order', ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Customer')
    phone = fields.Char(string='WhatsApp Number Sent To')
    message = fields.Text(string='Message Sent')
    state = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('manual', 'Manually Sent'),
    ], string='Status', default='sent')
    error_message = fields.Text(string='Error Details')
    provider = fields.Selection([
        ('twilio', 'Twilio'),
        ('meta', 'Meta'),
    ], string='Provider Used')
    create_date = fields.Datetime(string='Sent At', readonly=True)

    def name_get(self):
        return [(rec.id, f"WA-{rec.pos_order_id.name or rec.id}") for rec in self]
