import random
import string
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosSpecialOfferGenerateWizard(models.TransientModel):
    _name = 'pos.special.offer.generate.wizard'
    _description = 'Generate Coupon Codes Wizard'

    offer_id         = fields.Many2one('pos.special.offer', string='Offer', required=True)
    generation_mode  = fields.Selection([
        ('random',  'Random Codes'),
        ('serial',  'Prefix + Serial Numbers'),
    ], string='Generation Mode', default='random', required=True)

    # ── Random mode ──────────────────────────────────────────────────────────
    count       = fields.Integer(string='Number of Codes to Generate', default=10)
    code_length = fields.Integer(string='Code Length (characters)', default=8)

    # ── Serial mode ───────────────────────────────────────────────────────────
    prefix       = fields.Char(string='Prefix',
        help='Letters prepended to every code, e.g. FON')
    serial_from  = fields.Integer(string='Serial From', default=1,
        help='Starting serial number, e.g. 1')
    serial_to    = fields.Integer(string='Serial To', default=100,
        help='Ending serial number (inclusive), e.g. 100')
    serial_padding = fields.Integer(string='Number Padding (digits)', default=6,
        help='Zero-pad serials to this width. 6 → 000001, 000002 …')

    # ── Preview ───────────────────────────────────────────────────────────────
    preview = fields.Char(string='Preview', compute='_compute_preview')

    @api.depends('generation_mode', 'prefix', 'serial_from', 'serial_padding',
                 'code_length')
    def _compute_preview(self):
        for rec in self:
            if rec.generation_mode == 'serial':
                pfx = (rec.prefix or '').strip().upper()
                pad = max(1, rec.serial_padding or 6)
                start = rec.serial_from or 1
                ex1 = f"{pfx}{str(start).zfill(pad)}"
                ex2 = f"{pfx}{str(start + 1).zfill(pad)}"
                ex3 = f"{pfx}{str(start + 2).zfill(pad)}"
                rec.preview = f"{ex1},  {ex2},  {ex3},  …"
            else:
                chars = string.ascii_uppercase + string.digits
                ln = max(1, rec.code_length or 8)
                samples = [''.join(random.choices(chars, k=ln)) for _ in range(3)]
                rec.preview = ',  '.join(samples) + ',  …'

    # ── Constraints ───────────────────────────────────────────────────────────
    @api.constrains('generation_mode', 'serial_from', 'serial_to', 'count',
                    'code_length', 'serial_padding')
    def _check_fields(self):
        for rec in self:
            if rec.generation_mode == 'serial':
                if rec.serial_from < 0:
                    raise ValidationError('Serial From must be 0 or greater.')
                if rec.serial_to < rec.serial_from:
                    raise ValidationError('Serial To must be greater than or equal to Serial From.')
                total = rec.serial_to - rec.serial_from + 1
                if total > 100000:
                    raise ValidationError(
                        f'Range produces {total:,} codes. Maximum allowed is 100,000 at once.')
                if (rec.serial_padding or 0) < 1:
                    raise ValidationError('Number Padding must be at least 1.')
            else:
                if (rec.count or 0) < 1:
                    raise ValidationError('Number of Codes must be at least 1.')
                if (rec.code_length or 0) < 4:
                    raise ValidationError('Code Length must be at least 4.')

    # ── Generate action ───────────────────────────────────────────────────────
    def action_generate(self):
        self.ensure_one()
        Coupon = self.env['pos.special.offer.coupon']
        existing = set(Coupon.search([]).mapped('code'))
        created = 0

        if self.generation_mode == 'serial':
            pfx = (self.prefix or '').strip().upper()
            pad = max(1, self.serial_padding or 6)
            codes_to_create = []
            for n in range(self.serial_from, self.serial_to + 1):
                code = f"{pfx}{str(n).zfill(pad)}"
                if code in existing:
                    continue
                codes_to_create.append({
                    'offer_id':   self.offer_id.id,
                    'code':       code,
                    'single_use': True,
                })
                existing.add(code)

            # Batch create for performance
            Coupon.create(codes_to_create)
            created = len(codes_to_create)

        else:
            # Random mode (original behaviour)
            chars = string.ascii_uppercase + string.digits
            attempts = 0
            while created < self.count and attempts < self.count * 20:
                attempts += 1
                code = ''.join(random.choices(chars, k=self.code_length))
                if code in existing:
                    continue
                Coupon.create({
                    'offer_id':   self.offer_id.id,
                    'code':       code,
                    'single_use': True,
                })
                existing.add(code)
                created += 1

        return {
            'type': 'ir.actions.act_window',
            'name': f'Generated {created} Coupon Codes — {self.offer_id.name}',
            'res_model': 'pos.special.offer.coupon',
            'view_mode': 'list,form',
            'domain': [('offer_id', '=', self.offer_id.id)],
            'context': {'default_offer_id': self.offer_id.id},
            'target': 'current',
        }


# import random
# import string
# from odoo import models, fields, api
#
#
# class PosSpecialOfferGenerateWizard(models.TransientModel):
#     _name = 'pos.special.offer.generate.wizard'
#     _description = 'Generate Coupon Codes Wizard'
#
#     offer_id    = fields.Many2one('pos.special.offer', string='Offer', required=True)
#     count       = fields.Integer(string='Number of Codes to Generate', default=10, required=True)
#     code_length = fields.Integer(string='Code Length (characters)', default=8)
#
#     def action_generate(self):
#         self.ensure_one()
#         Coupon = self.env['pos.special.offer.coupon']
#         existing = set(Coupon.search([]).mapped('code'))
#
#         chars    = string.ascii_uppercase + string.digits
#         created  = 0
#         attempts = 0
#
#         while created < self.count and attempts < self.count * 20:
#             attempts += 1
#             code = ''.join(random.choices(chars, k=self.code_length))
#             if code in existing:
#                 continue
#             Coupon.create({
#                 'offer_id':  self.offer_id.id,
#                 'code':      code,
#                 'single_use': True,
#             })
#             existing.add(code)
#             created += 1
#
#         # Return to coupon list view
#         return {
#             'type': 'ir.actions.act_window',
#             'name': f'Generated {created} Coupon Codes — {self.offer_id.name}',
#             'res_model': 'pos.special.offer.coupon',
#             'view_mode': 'list,form',
#             'domain': [('offer_id', '=', self.offer_id.id)],
#             'context': {'default_offer_id': self.offer_id.id},
#             'target': 'current',
#         }
