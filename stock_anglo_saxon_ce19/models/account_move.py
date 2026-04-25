# -*- coding: utf-8 -*-
"""
account_move.py [v6]

The Anglo-Saxon journal entry is now created at RECEIPT VALIDATION (stock_picking.py).
The vendor bill should remain as standard Odoo 19 behavior:
    DR  230300 Stock Interim (Received)
    CR  211000 Account Payable

No additional lines are added to the vendor bill.
This file is kept minimal — all logic is in stock_picking.py.
"""
# No overrides needed on account.move.
# All Anglo-Saxon logic is handled in stock_picking.py on receipt validation.
