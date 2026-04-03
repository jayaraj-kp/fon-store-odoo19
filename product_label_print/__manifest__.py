{
    'name': 'Product Label Print - GP1125T',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Print custom product labels for GP-1125T thermal printer',
    'author': 'Custom',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_label_wizard_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
