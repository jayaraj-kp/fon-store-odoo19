# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ── Margin Block ──────────────────────────────────────────────────────────
    sale_margin_block_enabled = fields.Boolean(
        string='Block by Margin %',
        config_parameter='sale_margin_block.margin_block_enabled',
        help='If enabled, orders/invoices with margin below the minimum will be blocked.',
    )
    sale_margin_minimum = fields.Float(
        string='Minimum Margin (%)',
        config_parameter='sale_margin_block.margin_minimum',
        digits=(5, 2),
        default=0.0,
        help='Sales orders/invoices whose margin % is below this value will be blocked.',
    )

    # ── Cost Block ────────────────────────────────────────────────────────────
    sale_cost_block_enabled = fields.Boolean(
        string='Block by Cost Recovery %',
        config_parameter='sale_margin_block.cost_block_enabled',
        help='If enabled, orders/invoices whose price is below a % of cost will be blocked.',
    )
    sale_cost_minimum = fields.Float(
        string='Minimum Cost Recovery (%)',
        config_parameter='sale_margin_block.cost_minimum',
        digits=(5, 2),
        default=100.0,
        help=(
            'The selling price must be at least this percentage of cost. '
            'E.g. 100 means price >= cost; 90 means price may be 10%% below cost.'
        ),
    )

    # ── Override ──────────────────────────────────────────────────────────────
    sale_margin_block_warn_only = fields.Boolean(
        string='Warn Only (no hard block)',
        config_parameter='sale_margin_block.warn_only',
        default=False,
        help=(
            'When enabled, users will see a warning but the order will NOT be '
            'hard-blocked. Managers can always override regardless of this setting.'
        ),
    )
