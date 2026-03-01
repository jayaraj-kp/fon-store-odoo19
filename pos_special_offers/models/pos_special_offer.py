from odoo import models, fields, api
from datetime import date


class PosSpecialOffer(models.Model):
    _name = 'pos.special.offer'
    _description = 'POS Special Offer'
    _order = 'date_from desc'

    name = fields.Char(string='Offer Name', required=True)
    offer_type = fields.Selection([
        ('flat_discount', 'Flat Discount'),
        ('coupon',        'Coupon'),
    ], string='Offer Type', required=True, default='flat_discount')
    coupon_code = fields.Char(string='Coupon Code')
    product_ids = fields.Many2many(
        'product.product', 'pos_offer_product_rel', 'offer_id', 'product_id', string='Products')
    category_ids = fields.Many2many(
        'pos.category', 'pos_offer_category_rel', 'offer_id', 'category_id', string='POS Categories')
    date_from = fields.Date(string='From Date', required=True)
    date_to   = fields.Date(string='To Date',   required=True)
    active_time   = fields.Float(string='Active From Time')
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed',      'Fixed Price'),
    ], string='Discount Type', required=True, default='percentage')
    discount_value = fields.Float(string='Discount Value', required=True)
    purchase_limit = fields.Integer(string='Purchase Limit', default=0)
    usage_count    = fields.Integer(string='Times Used', default=0, readonly=True)
    active = fields.Boolean(default=True)

    state = fields.Selection([
        ('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'),
    ], compute='_compute_state', string='Status')

    @api.depends('date_from', 'date_to', 'active', 'purchase_limit', 'usage_count')
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.active:
                rec.state = 'draft'
            elif rec.purchase_limit and rec.usage_count >= rec.purchase_limit:
                rec.state = 'expired'
            elif rec.date_to and rec.date_to < today:
                rec.state = 'expired'
            elif rec.date_from and rec.date_from <= today <= rec.date_to:
                rec.state = 'active'
            else:
                rec.state = 'draft'

    @api.model
    def get_active_offers_for_pos(self):
        """
        Return all date-valid active offers.
        Time filtering is intentionally done client-side in JS
        to avoid UTC/local timezone mismatch on the server.
        Purchase limit check is done here.
        """
        today = fields.Date.today()
        offers = self.search([
            ('active', '=', True),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ])
        result = []
        for o in offers:
            # Skip if purchase limit reached
            if o.purchase_limit and o.usage_count >= o.purchase_limit:
                continue
            result.append({
                'id':             o.id,
                'name':           o.name,
                'offer_type':     o.offer_type,
                'coupon_code':    o.coupon_code or '',
                'product_ids':    o.product_ids.ids,
                'category_ids':   o.category_ids.ids,
                'discount_type':  o.discount_type,
                'discount_value': o.discount_value,
                'purchase_limit': o.purchase_limit,
                'usage_count':    o.usage_count,
                'date_from':      str(o.date_from),
                'date_to':        str(o.date_to),
                'active_time':    o.active_time,
            })
        return result

    def increment_usage(self):
        for rec in self:
            rec.usage_count += 1
