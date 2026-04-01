# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

# Indian currency denominations (stored as integer, e.g. 100 = ₹1, 50000 = ₹500)
INDIAN_DENOMINATIONS = [
    200000,  # ₹2000
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


def post_init_hook(env):
    """
    Runs ONCE immediately after this module is installed.
    Fixes ALL currently existing POS terminals by ensuring
    all Indian denominations exist in pos.bill.
    """
    _logger.info("POS Default Denomination: Running post_init_hook to fix existing POS terminals...")

    PosBill = env['pos.bill']

    fixed_count = 0
    for value in INDIAN_DENOMINATIONS:
        existing = PosBill.search([('value', '=', value)], limit=1)
        if not existing:
            PosBill.create({'value': value})
            _logger.info(
                "POS Default Denomination: Created missing denomination value=%s (₹%s)",
                value, value / 100
            )
            fixed_count += 1
        else:
            _logger.info(
                "POS Default Denomination: Denomination value=%s (₹%s) already exists.",
                value, value / 100
            )

    all_pos = env['pos.config'].search([])
    _logger.info(
        "POS Default Denomination: post_init_hook complete. "
        "Created %s missing denominations. All %s POS terminals now have denominations available.",
        fixed_count, len(all_pos)
    )
