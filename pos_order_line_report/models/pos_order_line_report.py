# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosOrderLineReport(models.Model):
    """
    Extends pos.order.line to add computed margin fields.
    All custom fields use the prefix 'rpt_' to avoid
    any collision with existing Odoo 19 fields.
    """
    _inherit = 'pos.order.line'

    # ── Margin computed fields ────────────────────────────────────────────────

    rpt_margin = fields.Float(
        string='Gross Margin',
        compute='_compute_rpt_margin',
        store=True,
        digits='Account',
        help='Revenue (incl. tax) minus Cost (standard price x qty)',
    )

    rpt_margin_percent = fields.Float(
        string='Margin %',
        compute='_compute_rpt_margin',
        store=True,
        digits=(16, 2),
        help='Gross margin as a percentage of revenue',
    )

    rpt_cost_total = fields.Float(
        string='Total Cost',
        compute='_compute_rpt_margin',
        store=True,
        digits='Account',
        help='standard_price x qty',
    )

    @api.depends(
        'qty',
        'price_subtotal_incl',
        'product_id',
        'product_id.standard_price',
    )
    def _compute_rpt_margin(self):
        for line in self:
            cost = line.qty * (line.product_id.standard_price or 0.0)
            revenue = line.price_subtotal_incl or 0.0
            margin = revenue - cost
            line.rpt_cost_total = cost
            line.rpt_margin = margin
            line.rpt_margin_percent = (
                (margin / revenue * 100.0) if revenue else 0.0
            )

    # ── Related fields for grouping (all prefixed rpt_) ───────────────────────

    rpt_product_category_id = fields.Many2one(
        comodel_name='product.category',
        related='product_id.categ_id',
        string='Product Category',
        store=True,
        readonly=True,
    )

    rpt_order_date = fields.Datetime(
        related='order_id.date_order',
        string='Sale Date',
        store=True,
        readonly=True,
    )

    rpt_order_state = fields.Selection(
        related='order_id.state',
        string='Order Status',
        store=True,
        readonly=True,
    )

    rpt_customer_id = fields.Many2one(
        comodel_name='res.partner',
        related='order_id.partner_id',
        string='Customer',
        store=True,
        readonly=True,
    )

    rpt_session_id = fields.Many2one(
        comodel_name='pos.session',
        related='order_id.session_id',
        string='POS Session',
        store=True,
        readonly=True,
    )
