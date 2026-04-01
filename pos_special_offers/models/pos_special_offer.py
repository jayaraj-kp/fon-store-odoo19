from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, date


class PosSpecialOffer(models.Model):
    _name = 'pos.special.offer'
    _description = 'POS Special Offer'
    _order = 'date_from desc'

    name       = fields.Char(string='Offer Name', required=True)
    offer_type = fields.Selection([
        ('flat_discount', 'Flat Discount'),
        ('coupon',        'Coupon'),
    ], string='Offer Type', required=True, default='flat_discount')

    # ── Warehouse restriction ─────────────────────────────────────────────────
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Restrict this offer to users whose default warehouse matches. '
             'Leave empty to show the offer in all warehouses.'
    )

    # ── Coupon settings ──────────────────────────────────────────────────────
    coupon_code     = fields.Char(string='Single Coupon Code',
        help='Used when offer type is Coupon and no generated codes exist.')
    coupon_ids      = fields.One2many('pos.special.offer.coupon', 'offer_id',
        string='Generated Coupon Codes')
    coupon_count    = fields.Integer(string='Total Codes',   compute='_compute_coupon_counts')
    available_count = fields.Integer(string='Available',     compute='_compute_coupon_counts')
    used_count_total= fields.Integer(string='Used',          compute='_compute_coupon_counts')

    @api.depends('coupon_ids', 'coupon_ids.state')
    def _compute_coupon_counts(self):
        for rec in self:
            rec.coupon_count     = len(rec.coupon_ids)
            rec.available_count  = len(rec.coupon_ids.filtered(lambda c: c.state == 'available'))
            rec.used_count_total = len(rec.coupon_ids.filtered(lambda c: c.state == 'used'))

    # ── Scope toggles ────────────────────────────────────────────────────────
    all_products   = fields.Boolean(string='All Products',   default=False)
    all_categories = fields.Boolean(string='All Categories', default=False)

    product_ids  = fields.Many2many(
        'product.product', 'pos_offer_product_rel',
        'offer_id', 'product_id', string='Products')
    category_ids = fields.Many2many(
        'product.category', 'pos_offer_category_rel',
        'offer_id', 'category_id', string='Product Categories')

    # ── Exclusion lists ───────────────────────────────────────────────────────
    exclude_product_ids  = fields.Many2many(
        'product.product', 'pos_offer_excl_product_rel',
        'offer_id', 'product_id', string='Exclude Products',
        help='These products will NOT receive the discount even if they match the include scope.')
    exclude_category_ids = fields.Many2many(
        'product.category', 'pos_offer_excl_category_rel',
        'offer_id', 'category_id', string='Exclude Categories',
        help='Products in these categories will NOT receive the discount even if they match the include scope.')

    date_from     = fields.Datetime(string='Start Date & Time', required=True)
    date_to       = fields.Datetime(string='End Date & Time',   required=True)
    discount_type = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fixed',      'Fixed Price'),
    ], string='Discount Type', required=True, default='percentage')
    discount_value = fields.Float(string='Discount Value', required=True)
    purchase_limit = fields.Integer(string='Purchase Limit', default=0)
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
                rec.state = 'active' if dt_from <= now <= dt_to else 'draft'
            else:
                rec.state = 'draft'

    @api.depends('date_to')
    def _compute_days_remaining(self):
        today = date.today()
        for rec in self:
            rec.days_remaining = max((rec.date_to.date() - today).days, 0) if rec.date_to else 0

    @api.onchange('all_products')
    def _onchange_all_products(self):
        if self.all_products:
            self.product_ids = [(5, 0, 0)]

    @api.onchange('all_categories')
    def _onchange_all_categories(self):
        if self.all_categories:
            self.category_ids = [(5, 0, 0)]

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError('Start Date & Time must be before End Date & Time.')

    @api.constrains('offer_type', 'coupon_code')
    def _check_coupon_code(self):
        for rec in self:
            if rec.offer_type == 'coupon' and not rec.coupon_code and not rec.coupon_ids:
                raise ValidationError(
                    'Coupon offers require either a Coupon Code or generated coupon codes.')

    @api.constrains('discount_value')
    def _check_discount_value(self):
        for rec in self:
            if rec.discount_value <= 0:
                raise ValidationError('Discount Value must be greater than 0.')
            if rec.discount_type == 'percentage' and rec.discount_value > 100:
                raise ValidationError('Percentage discount cannot exceed 100%.')

    # ── Generate coupons wizard button ───────────────────────────────────────
    def action_generate_coupons(self):
        self.ensure_one()
        return {
            'name': 'Generate Coupon Codes',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.special.offer.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_offer_id': self.id},
        }

    # ── Export CSV button ─────────────────────────────────────────────────────
    def action_export_coupons_csv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/pos_special_offers/export_coupons/{self.id}',
            'target': 'new',
        }

    # ── View all coupons button ───────────────────────────────────────────────
    def action_view_coupons(self):
        self.ensure_one()
        return {
            'name': f'Coupon Codes — {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.special.offer.coupon',
            'view_mode': 'list,form',
            'domain': [('offer_id', '=', self.id)],
            'context': {'default_offer_id': self.id},
        }

    # ── POS RPC: return active offers filtered by session warehouse ───────────
    @api.model
    def get_active_offers_for_pos(self):
        now = fields.Datetime.now()

        # ── Resolve the warehouse of the current POS session ─────────────────
        # The POS session links to pos.config which has warehouse_id
        session_warehouse_id = False
        try:
            PosSession = self.env['pos.session']
            open_sessions = PosSession.search([
                ('state', '=', 'opened'),
                ('user_id', '=', self.env.uid),
            ], limit=1)
            if open_sessions:
                session_warehouse_id = open_sessions.config_id.warehouse_id.id
        except Exception:
            pass

        offers = self.search([
            ('active', '=', True),
            ('date_from', '<=', now),
            ('date_to',   '>=', now),
        ])

        result = []
        for o in offers:
            if o.purchase_limit and o.usage_count >= o.purchase_limit:
                continue

            # ── Warehouse filter ──────────────────────────────────────────────
            # If the offer has a warehouse set, only include it when the current
            # session's warehouse matches. Offers with no warehouse = show everywhere.
            if o.warehouse_id and session_warehouse_id:
                if o.warehouse_id.id != session_warehouse_id:
                    continue

            # Build list of valid coupon codes for POS
            generated_codes = []
            if o.offer_type == 'coupon' and o.coupon_ids:
                generated_codes = [
                    {'id': c.id, 'code': c.code, 'single_use': c.single_use}
                    for c in o.coupon_ids
                    if c.state == 'available'
                ]

            result.append({
                'id':              o.id,
                'name':            o.name,
                'offer_type':      o.offer_type,
                'coupon_code':     o.coupon_code or '',
                'generated_codes': generated_codes,
                'all_products':    o.all_products,
                'all_categories':  o.all_categories,
                'product_ids':          o.product_ids.ids,
                'category_ids':         o.category_ids.ids,
                'exclude_product_ids':  o.exclude_product_ids.ids,
                'exclude_category_ids': o.exclude_category_ids.ids,
                'discount_type':   o.discount_type,
                'discount_value':  o.discount_value,
                'purchase_limit':  o.purchase_limit,
                'usage_count':     o.usage_count,
                'date_from':       str(o.date_from),
                'date_to':         str(o.date_to),
                'warehouse_id':    o.warehouse_id.id or False,
                'warehouse_name':  o.warehouse_id.name or '',
            })
        return result

    # ── POS RPC: mark a generated coupon as used ──────────────────────────────
    @api.model
    def mark_coupon_used(self, coupon_id):
        coupon = self.env['pos.special.offer.coupon'].browse(coupon_id)
        if coupon.exists():
            coupon.mark_used()
            return True
        return False

    def increment_usage(self):
        for rec in self:
            rec.usage_count += 1