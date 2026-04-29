import string
import random
from odoo import models, fields, api


class PosSpecialOfferCoupon(models.Model):
    _name = 'pos.special.offer.coupon'
    _description = 'POS Special Offer Coupon Code'
    _order = 'create_date desc'

    offer_id   = fields.Many2one('pos.special.offer', string='Offer',
                                  required=True, ondelete='cascade')
    code       = fields.Char(string='Coupon Code', required=True, index=True)
    single_use = fields.Boolean(string='Single Use', default=True, readonly=True)
    used       = fields.Boolean(string='Used', default=False)
    used_count = fields.Integer(string='Times Used', default=0)
    active     = fields.Boolean(default=True)

    state = fields.Selection([
        ('available', 'Available'),
        ('used',      'Used'),
        ('expired',   'Expired'),
    ], compute='_compute_state', string='Status', store=True)

    @api.depends('used', 'active')
    def _compute_state(self):
        for rec in self:
            if not rec.active:
                rec.state = 'expired'
            elif rec.used:
                rec.state = 'used'
            else:
                rec.state = 'available'

    def mark_used(self):
        for rec in self:
            rec.used_count += 1
            rec.used = True   # always single-use

    def action_export_csv(self):
        """Export coupon codes for this offer as CSV download."""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos_special_offers/export_coupons/{self[0].offer_id.id}',
            'target': 'new',
        }
