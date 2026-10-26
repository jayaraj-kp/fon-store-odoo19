# -*- coding: utf-8 -*-
{
    "name": "POS Pricelist Date Guard",
    "summary": "Make POS respect pricelist rule start and end dates when a product is added",
    "description": """
In Odoo 19 POS, pricelist rules are loaded when the POS page opens and the
price calculation (findBestRule) only compares the minimum quantity. A rule
that has expired (or has not started yet) is still applied until POS is
reloaded.

This module makes POS check the rule's Start Date and End Date every time a
price is calculated, so a rule such as 300 from 26/10 to 30/10 stops applying
at its end time even in a POS tab that stays open.
    """,
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_pricelist_date_guard/static/src/js/pricelist_date_guard.js",
        ],
    },
    "installable": True,
    "application": False,
}
