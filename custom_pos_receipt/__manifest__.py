{
    'name': 'Custom POS Receipt',
    'version': '19.0.1.0.0',
    'summary': 'Customize POS Receipt (Odoo 17/18/19 OWL)',
    'category': 'Point of Sale',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_receipt/static/src/xml/order_receipt.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
