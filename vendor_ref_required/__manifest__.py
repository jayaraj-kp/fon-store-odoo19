{
    'name': 'Vendor Reference Required',
    'version': '1.0',
    'summary': 'Makes Vendor Reference required and displays dates in dd/mm/yyyy format without time',
    'author': 'Custom',
    'depends': ['purchase'],
    'data': [
        'data/lang_date_format.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
