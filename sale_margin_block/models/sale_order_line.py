# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ── Unit cost (pulled from product standard_price in company currency) ───
    smb_unit_cost = fields.Float(
        string='Unit Cost',
        compute='_compute_smb_cost_margin',
        store=True,
        digits='Product Price',
    )

    # ── Computed margin fields ────────────────────────────────────────────────
    smb_margin_amount = fields.Monetary(
        string='Margin Amount',
        compute='_compute_smb_cost_margin',
        store=True,
        currency_field='currency_id',
    )
    smb_margin_percent = fields.Float(
        string='Margin %',
        compute='_compute_smb_cost_margin',
        store=True,
        digits=(5, 2),
    )
    smb_cost_recovery_percent = fields.Float(
        string='Cost Recovery %',
        compute='_compute_smb_cost_margin',
        store=True,
        digits=(5, 2),
        help='(Unit Price / Unit Cost) * 100. 100 means break-even.',
    )

    # ── Warning flag (non-stored, for UI colour) ──────────────────────────────
    smb_below_threshold = fields.Boolean(
        string='Below Threshold',
        compute='_compute_smb_below_threshold',
    )

    @api.depends(
        'product_id', 'price_unit', 'product_uom_qty',
        'discount', 'currency_id', 'order_id.currency_id',
    )
    def _compute_smb_cost_margin(self):
        for line in self:
            cost = 0.0
            if line.product_id:
                cost = line.product_id.standard_price
                # Convert cost currency (product → order currency if they differ)
                if (
                    line.product_id.cost_currency_id
                    and line.currency_id
                    and line.product_id.cost_currency_id != line.currency_id
                ):
                    cost = line.product_id.cost_currency_id._convert(
                        cost,
                        line.currency_id,
                        line.company_id or line.order_id.company_id,
                        line.order_id.date_order or fields.Date.today(),
                    )

            line.smb_unit_cost = cost

            # Effective unit price after discount
            effective_price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            qty = line.product_uom_qty or 0.0

            subtotal = effective_price * qty
            total_cost = cost * qty

            margin_amount = subtotal - total_cost
            line.smb_margin_amount = margin_amount

            if subtotal:
                line.smb_margin_percent = (margin_amount / subtotal) * 100.0
            else:
                line.smb_margin_percent = 0.0

            if cost:
                line.smb_cost_recovery_percent = (effective_price / cost) * 100.0
            else:
                # No cost → always OK
                line.smb_cost_recovery_percent = 100.0

    @api.depends('smb_margin_percent', 'smb_cost_recovery_percent')
    def _compute_smb_below_threshold(self):
        ICP = self.env['ir.config_parameter'].sudo()
        margin_enabled = ICP.get_param('sale_margin_block.margin_block_enabled', 'False') == 'True'
        margin_min = float(ICP.get_param('sale_margin_block.margin_minimum', '0'))
        cost_enabled = ICP.get_param('sale_margin_block.cost_block_enabled', 'False') == 'True'
        cost_min = float(ICP.get_param('sale_margin_block.cost_minimum', '100'))

        for line in self:
            below = False
            if line.product_id:
                if margin_enabled and line.smb_margin_percent < margin_min:
                    below = True
                if cost_enabled and line.smb_cost_recovery_percent < cost_min:
                    below = True
            line.smb_below_threshold = below
