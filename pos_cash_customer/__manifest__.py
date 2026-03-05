{
    'name': 'POS Cash Customer',
    'version': '1.0.0',
    'category': 'Point of Sale',
    'summary': 'Auto-assign new POS customers as contacts under a single CASH CUSTOMER partner',
    'description': """
        This module ensures all new customers created from POS are added
        as contacts under a single 'CASH CUSTOMER' partner.
        - First time: prompts to create the CASH CUSTOMER partner
        - After that: opens Create Contact form directly under CASH CUSTOMER
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer/static/src/js/cash_customer_patch.js',
            'pos_cash_customer/static/src/xml/cash_customer.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
