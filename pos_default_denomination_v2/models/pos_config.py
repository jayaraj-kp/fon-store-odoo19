# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

INDIAN_DENOMINATIONS = [
    50000,   # ₹500
    20000,   # ₹200
    10000,   # ₹100
    5000,    # ₹50
    2000,    # ₹20
    1000,    # ₹10
    500,     # ₹5
    200,     # ₹2
    100,     # ₹1
]


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create: whenever a new POS is created,
        ensure all Indian denominations exist in pos.bill.
        """
        configs = super().create(vals_list)
        for config in configs:
            config._ensure_indian_denominations()
        return configs

    def _ensure_indian_denominations(self):
        """
        Create any missing Indian denomination entries in pos.bill.
        Since pos.bill is global (not per-POS), adding here makes them
        available in the Coins/Notes popup for all POS terminals.
        """
        self.ensure_one()
        PosBill = self.env['pos.bill']

        for value in INDIAN_DENOMINATIONS:
            existing = PosBill.search([('value', '=', value)], limit=1)
            if not existing:
                PosBill.create({'value': value})
                _logger.info(
                    "POS Default Denomination: Auto-created denomination ₹%s "
                    "for new POS '%s'.", value / 100, self.name
                )
