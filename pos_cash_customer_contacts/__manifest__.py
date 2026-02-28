{
    'name': 'POS Cash Customer Contacts Filter',
    'version': '19.0.1.0.0',
    'summary': 'Show only Cash Customer contacts in POS customer selection',
    'description': """
        Filters the POS customer selection wizard to display only
        contacts (child partners) of the 'Cash Customer' record.
    """,
    'author': 'Custom',
    'category': 'Point of Sale',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer_contacts/static/src/js/customer_filter.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
