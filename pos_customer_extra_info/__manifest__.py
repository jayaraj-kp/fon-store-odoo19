{
    'name': 'POS Customer Extra Info',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Show last invoice number, last visit time, invoice count and tags in POS customer list',
    'author': 'Custom',
    'depends': ['point_of_sale', 'account'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_extra_info/static/src/js/customer_list_patch.js',
            'pos_customer_extra_info/static/src/xml/customer_list_patch.xml',
            'pos_customer_extra_info/static/src/css/customer_list.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
