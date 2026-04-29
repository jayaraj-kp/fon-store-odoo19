# -*- coding: utf-8 -*-
# account_report.py
#
# account.report is an Enterprise-only model in Odoo 19.
# In Community Edition, accounting reports are rendered via ir.actions.report
# or account.move views — not through account.report.
#
# Restriction enforcement for CE is done entirely in JavaScript:
#   - Menu items are hidden by access_restrictions.js matching menu label text.
#
# This file is intentionally left as a no-op to avoid import errors on CE.
