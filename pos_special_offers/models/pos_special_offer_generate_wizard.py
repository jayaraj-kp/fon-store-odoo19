import random
import string
from odoo import models, fields, api


class PosSpecialOfferGenerateWizard(models.TransientModel):
    _name = 'pos.special.offer.generate.wizard'
    _description = 'Generate Coupon Codes Wizard'

    offer_id    = fields.Many2one('pos.special.offer', string='Offer', required=True)
    count       = fields.Integer(string='Number of Codes to Generate', default=10, required=True)
    code_length = fields.Integer(string='Code Length (characters)', default=8)

    def action_generate(self):
        self.ensure_one()
        Coupon = self.env['pos.special.offer.coupon']
        existing = set(Coupon.search([]).mapped('code'))

        chars    = string.ascii_uppercase + string.digits
        created  = 0
        attempts = 0

        while created < self.count and attempts < self.count * 20:
            attempts += 1
            code = ''.join(random.choices(chars, k=self.code_length))
            if code in existing:
                continue
            Coupon.create({
                'offer_id':  self.offer_id.id,
                'code':      code,
                'single_use': True,
            })
            existing.add(code)
            created += 1

        # Return to coupon list view
        return {
            'type': 'ir.actions.act_window',
            'name': f'Generated {created} Coupon Codes — {self.offer_id.name}',
            'res_model': 'pos.special.offer.coupon',
            'view_mode': 'list,form',
            'domain': [('offer_id', '=', self.offer_id.id)],
            'context': {'default_offer_id': self.offer_id.id},
            'target': 'current',
        }
