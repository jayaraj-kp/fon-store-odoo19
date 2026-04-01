# -*- coding: utf-8 -*-
{
    'name': 'POS Default Indian Denominations',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Auto-create Indian currency denominations for ALL existing and future POS',
    'description': """
        On Installation:
        ----------------
        - Automatically fixes ALL currently existing POS terminals that are
          missing Indian currency Coins/Bills denominations.

        On Every New POS Created (Future):
        -----------------------------------
        - Automatically populates Indian currency Coins/Bills denominations
          (₹2000, ₹500, ₹200, ₹100, ₹50, ₹20, ₹10, ₹5, ₹2, ₹1)
          whenever a new Point of Sale is created.

        No more manual setup required — ever.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'data/pos_denomination_data.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
