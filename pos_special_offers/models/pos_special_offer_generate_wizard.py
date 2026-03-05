import random
import string
from odoo import models, fields, api


class PosSpecialOfferGenerateWizard(models.TransientModel):
    _name = 'pos.special.offer.generate.wizard'
    _description = 'Generate Coupon Codes Wizard'

    offer_id    = fields.Many2one('pos.special.offer', string='Offer', required=True)
    prefix      = fields.Char(string='Code Prefix', help='e.g. RAMADAN → RAMADAN-A3X9')
    count       = fields.Integer(string='Number of Codes', default=10, required=True)
    code_length = fields.Integer(string='Random Part Length', default=6)
    single_use  = fields.Boolean(string='Single Use per Code', default=True,
        help='Each code can only be used once.')

    def action_generate(self):
        self.ensure_one()
        Coupon = self.env['pos.special.offer.coupon']
        existing_codes = set(Coupon.search([]).mapped('code'))

        created = 0
        attempts = 0
        max_attempts = self.count * 10

        while created < self.count and attempts < max_attempts:
            attempts += 1
            chars = string.ascii_uppercase + string.digits
            rand  = ''.join(random.choices(chars, k=self.code_length))
            code  = f"{self.prefix.strip().upper()}-{rand}" if self.prefix else rand

            if code in existing_codes:
                continue

            Coupon.create({
                'offer_id':   self.offer_id.id,
                'code':       code,
                'single_use': self.single_use,
            })
            existing_codes.add(code)
            created += 1

        return {
            'type': 'ir.actions.act_window',
            'name': f'Generated {created} Coupon Codes',
            'res_model': 'pos.special.offer.coupon',
            'view_mode': 'list',
            'domain': [('offer_id', '=', self.offer_id.id)],
            'context': {'default_offer_id': self.offer_id.id},
        }
