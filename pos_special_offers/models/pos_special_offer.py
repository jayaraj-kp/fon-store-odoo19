from odoo import models, fields, api
from datetime import datetime, date


class PosSpecialOffer(models.Model):
    _name = 'pos.special.offer'
    _description = 'POS Special Offer'
    _order = 'date_from desc'

    name = fields.Char(string='Offer Name', required=True)
    product_ids = fields.Many2many(
        'product.product',
        'pos_offer_product_rel',
        'offer_id', 'product_id',
        string='Products'
    )
    category_ids = fields.Many2many(
        'pos.category',
        'pos_offer_category_rel',
        'offer_id', 'category_id',
        string='POS Categories'
    )
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    active_time = fields.Float(
        string='Active From Time',
        help='Time of day when offer becomes active (24h format, e.g. 12.5 = 12:30)'
    )
    discount_type = fields.Selection([
        ('percentage', 'Percentage Discount (%)'),
        ('fixed', 'Fixed Price'),
    ], default='percentage', string='Discount Type', required=True)
    discount_value = fields.Float(string='Discount Value', required=True)
    active = fields.Boolean(default=True, string='Active')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], compute='_compute_state', string='Status', store=False)

    @api.depends('date_from', 'date_to', 'active')
    def _compute_state(self):
        today = date.today()
        for rec in self:
            if not rec.active:
                rec.state = 'draft'
            elif rec.date_to and rec.date_to < today:
                rec.state = 'expired'
            elif rec.date_from and rec.date_from <= today <= rec.date_to:
                rec.state = 'active'
            else:
                rec.state = 'draft'

    @api.model
    def get_active_offers_for_pos(self):
        """Called from POS to load currently active offers."""
        today = fields.Date.today()
        now_hour = datetime.now().hour + datetime.now().minute / 60.0

        offers = self.search([
            ('active', '=', True),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ])

        result = []
        for offer in offers:
            # Check time restriction
            if offer.active_time and now_hour < offer.active_time:
                continue
            result.append({
                'id': offer.id,
                'name': offer.name,
                'product_ids': offer.product_ids.ids,
                'category_ids': offer.category_ids.ids,
                'discount_type': offer.discount_type,
                'discount_value': offer.discount_value,
            })
        return result
