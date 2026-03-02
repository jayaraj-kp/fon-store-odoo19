from odoo import models, fields, api
from datetime import datetime, date


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

    # ── All Products / All Categories toggles ──
    all_products   = fields.Boolean(string='All Products',   default=False,
        help='If checked, offer applies to ALL products regardless of selection below.')
    all_categories = fields.Boolean(string='All Categories', default=False,
        help='If checked, offer applies to ALL product categories regardless of selection below.')

    product_ids  = fields.Many2many(
        'product.product', 'pos_offer_product_rel',
        'offer_id', 'product_id', string='Products')
    category_ids = fields.Many2many(
        'product.category', 'pos_offer_category_rel',
        'offer_id', 'category_id', string='Product Categories')

    date_from     = fields.Datetime(string='Start Date & Time', required=True)
    date_to       = fields.Datetime(string='End Date & Time',   required=True)
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed',      'Fixed Price'),
    ], string='Discount Type', required=True, default='percentage')
    discount_value = fields.Float(string='Discount Value', required=True)
    purchase_limit = fields.Integer(string='Purchase Limit', default=0,
        help='Max times this offer can be used. 0 = unlimited.')
    usage_count    = fields.Integer(string='Times Used', default=0, readonly=True)
    active         = fields.Boolean(default=True)

    state = fields.Selection([
        ('draft',   'Draft'),
        ('active',  'Active'),
        ('expired', 'Expired'),
    ], compute='_compute_state', string='Status', store=True)

    days_remaining = fields.Integer(string='Days Remaining', compute='_compute_days_remaining')

    @api.depends('date_from', 'date_to', 'active', 'purchase_limit', 'usage_count')
    def _compute_state(self):
        now = datetime.now()
        for rec in self:
            if not rec.active:
                rec.state = 'draft'
            elif rec.purchase_limit and rec.usage_count >= rec.purchase_limit:
                rec.state = 'expired'
            elif rec.date_to and fields.Datetime.from_string(str(rec.date_to)) < now:
                rec.state = 'expired'
            elif rec.date_from and rec.date_to:
                dt_from = fields.Datetime.from_string(str(rec.date_from))
                dt_to   = fields.Datetime.from_string(str(rec.date_to))
                if dt_from <= now <= dt_to:
                    rec.state = 'active'
                else:
                    rec.state = 'draft'
            else:
                rec.state = 'draft'

    @api.depends('date_to')
    def _compute_days_remaining(self):
        today = date.today()
        for rec in self:
            rec.days_remaining = max((rec.date_to.date() - today).days, 0) if rec.date_to else 0

    # Auto-clear individual selections when "All" is toggled on
    @api.onchange('all_products')
    def _onchange_all_products(self):
        if self.all_products:
            self.product_ids = [(5, 0, 0)]  # clear all

    @api.onchange('all_categories')
    def _onchange_all_categories(self):
        if self.all_categories:
            self.category_ids = [(5, 0, 0)]  # clear all

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise models.ValidationError('Start Date & Time must be before End Date & Time.')

    @api.constrains('offer_type', 'coupon_code')
    def _check_coupon_code(self):
        for rec in self:
            if rec.offer_type == 'coupon' and not rec.coupon_code:
                raise models.ValidationError('Coupon Code is required for Coupon type offers.')

    @api.constrains('discount_value')
    def _check_discount_value(self):
        for rec in self:
            if rec.discount_value <= 0:
                raise models.ValidationError('Discount Value must be greater than 0.')
            if rec.discount_type == 'percentage' and rec.discount_value > 100:
                raise models.ValidationError('Percentage discount cannot exceed 100%.')

    @api.model
    def get_active_offers_for_pos(self):
        now = fields.Datetime.now()
        offers = self.search([
            ('active', '=', True),
            ('date_from', '<=', now),
            ('date_to',   '>=', now),
        ])
        result = []
        for o in offers:
            if o.purchase_limit and o.usage_count >= o.purchase_limit:
                continue
            result.append({
                'id':             o.id,
                'name':           o.name,
                'offer_type':     o.offer_type,
                'coupon_code':    o.coupon_code or '',
                'all_products':   o.all_products,
                'all_categories': o.all_categories,
                'product_ids':    o.product_ids.ids,
                'category_ids':   o.category_ids.ids,
                'discount_type':  o.discount_type,
                'discount_value': o.discount_value,
                'purchase_limit': o.purchase_limit,
                'usage_count':    o.usage_count,
                'date_from':      str(o.date_from),
                'date_to':        str(o.date_to),
            })
        return result

    def increment_usage(self):
        for rec in self:
            rec.usage_count += 1
