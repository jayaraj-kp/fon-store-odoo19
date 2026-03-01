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
        string='Active From Time (24h)',
        default=0.0,
        help='Hour of the day from which this offer is active. e.g. 12.0 = 12:00 PM'
    )
    active_time_end = fields.Float(
        string='Active Until Time (24h)',
        default=23.99,
        help='Hour of the day until which this offer is active. e.g. 22.0 = 10:00 PM'
    )
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed', 'Fixed Price'),
    ], default='percentage', string='Discount Type', required=True)
    discount_value = fields.Float(string='Discount Value', default=10.0)
    active = fields.Boolean(default=True, string='Active')
    state = fields.Char(string='Status', compute='_compute_state')

    @api.depends('date_from', 'date_to', 'active')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if not rec.active:
                rec.state = 'inactive'
            elif rec.date_from > today:
                rec.state = 'upcoming'
            elif rec.date_to < today:
                rec.state = 'expired'
            else:
                rec.state = 'active'

    @api.model
    def get_active_offers_for_pos(self):
        """Called from POS to get currently active offers."""
        today = fields.Date.today()
        now_hour = datetime.now().hour + datetime.now().minute / 60.0

        offers = self.search([
            ('active', '=', True),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ])

        result = []
        for offer in offers:
            # Check time window
            if offer.active_time <= now_hour <= offer.active_time_end:
                result.append({
                    'id': offer.id,
                    'name': offer.name,
                    'product_ids': offer.product_ids.ids,
                    'category_ids': offer.category_ids.ids,
                    'discount_type': offer.discount_type,
                    'discount_value': offer.discount_value,
                    'date_from': str(offer.date_from),
                    'date_to': str(offer.date_to),
                    'active_time': offer.active_time,
                    'active_time_end': offer.active_time_end,
                })
        return result
