# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosOrderLineReport(models.Model):
    """
    Extends pos.order.line to add computed margin fields
    for use in the pivot/graph/list analysis report.
    """
    _inherit = 'pos.order.line'

    # ── Margin fields ─────────────────────────────────────────────────────────

    margin = fields.Float(
        string='Margin',
        compute='_compute_margin',
        store=True,
        digits='Account',
        help='Gross margin = Revenue (incl. tax) – Cost (standard price × qty)',
    )

    margin_percent = fields.Float(
        string='Margin (%)',
        compute='_compute_margin',
        store=True,
        digits=(16, 2),
        help='Margin as a percentage of revenue',
    )

    cost_price_total = fields.Float(
        string='Total Cost',
        compute='_compute_margin',
        store=True,
        digits='Account',
        help='standard_price × qty_ordered',
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends(
        'qty',
        'price_subtotal_incl',
        'product_id',
        'product_id.standard_price',
    )
    def _compute_margin(self):
        for line in self:
            cost = line.qty * (line.product_id.standard_price or 0.0)
            revenue = line.price_subtotal_incl or 0.0
            margin = revenue - cost

            line.cost_price_total = cost
            line.margin = margin
            line.margin_percent = (
                (margin / revenue * 100.0) if revenue else 0.0
            )

    # ── Convenience related fields for grouping ───────────────────────────────

    product_category_id = fields.Many2one(
        related='product_id.categ_id',
        string='Product Category',
        store=True,
        readonly=True,
    )

    order_date = fields.Date(
        related='order_id.date_order',
        string='Order Date',
        store=True,
        readonly=True,
    )

    order_state = fields.Selection(
        related='order_id.state',
        string='Order State',
        store=True,
        readonly=True,
    )

    session_id = fields.Many2one(
        related='order_id.session_id',
        string='POS Session',
        store=True,
        readonly=True,
    )

    pricelist_id = fields.Many2one(
        related='order_id.pricelist_id',
        string='Pricelist',
        store=True,
        readonly=True,
    )

    customer_id = fields.Many2one(
        related='order_id.partner_id',
        string='Customer',
        store=True,
        readonly=True,
    )
