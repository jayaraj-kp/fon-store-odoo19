{
    'name': 'Vendor Reference Required',
    'version': '1.0',
    'summary': 'Makes Vendor Reference required and displays dates in dd/mm/yyyy format without time',
    'author': 'Custom',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
