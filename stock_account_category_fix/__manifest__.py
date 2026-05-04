{
    'name': 'Stock Account Category Fix',
    'version': '19.0.1.1.0',
    'summary': 'Restores Account Stock Properties in Product Category + fixes AVCO interim account pricing for Odoo 19 CE',
    'description': """
        Fix 1 – Account Stock Properties (Product Category form)
        =========================================================
        In Odoo 19 Community Edition the Account Stock Properties fields
        (Stock Valuation Account, Stock Journal, Stock Input Account,
        Stock Output Account) are missing from the Product Category form
        when using Perpetual (Automated) valuation.
        This module restores those fields so Anglo-Saxon costing works correctly.

        Fix 2 – AVCO interim account pricing
        =====================================
        When a purchase receipt is validated for an AVCO-costed product,
        Odoo 19 CE credits the Stock Interim (Received) account at the new
        moving-average cost instead of the actual PO price.  This leaves a
        permanent residual in the interim account that never clears when the
        vendor bill is posted.

        Example
        -------
        Opening  : 10 units @ 50  = 500
        Purchased: 10 units @ 55  = 550  →  new AVCO = 52.50

        CE (wrong) : Interim credited at 52.50 × 10 = 525
        Vendor bill: Interim debited  at 55.00 × 10 = 550  →  25 residual

        Fixed      : Interim credited at 55.00 × 10 = 550  →  zero residual
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock_account', 'purchase_stock'],
    'data': ['views/product_category_views.xml'],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}
