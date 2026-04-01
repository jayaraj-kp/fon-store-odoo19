# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)

# Indian currency denominations stored in RUPEES (pos.bill.value is float in rupees)
INDIAN_DENOMINATIONS = [500, 200, 100, 50, 20, 10, 5, 2, 1]


def post_init_hook(env):
    """
    Runs ONCE immediately after this module is installed.
    1. Deletes any wrong denomination values (old paise-based entries like 50000, 20000 etc.)
    2. Creates correct INR denominations (500, 200, 100, 50, 20, 10, 5, 2, 1)
    """
    _logger.info("POS Default Denomination: Running post_init_hook...")

    PosBill = env['pos.bill']

    # --- Step 1: Remove wrong old values (paise-based: 100, 200, 500, 1000... 200000) ---
    # These are values that are NOT in our correct list but look like paise conversions
    correct_values = set(INDIAN_DENOMINATIONS)
    all_bills = PosBill.search([])
    wrong_bills = all_bills.filtered(lambda b: b.value not in correct_values)
    if wrong_bills:
        _logger.info(
            "POS Default Denomination: Removing %s incorrect denomination(s): %s",
            len(wrong_bills), wrong_bills.mapped('value')
        )
        wrong_bills.unlink()

    # --- Step 2: Create correct denominations ---
    fixed_count = 0
    for value in INDIAN_DENOMINATIONS:
        existing = PosBill.search([('value', '=', value)], limit=1)
        if not existing:
            PosBill.create({'value': value})
            _logger.info("POS Default Denomination: Created ₹%s", value)
            fixed_count += 1
        else:
            _logger.info("POS Default Denomination: ₹%s already exists.", value)

    all_pos = env['pos.config'].search([])
    _logger.info(
        "POS Default Denomination: Done. Created %s denominations. %s POS terminal(s) now fixed.",
        fixed_count, len(all_pos)
    )
