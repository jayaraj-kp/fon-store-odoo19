# {
#     'name': 'Product Label Print - GP1125T',
#     'version': '19.0.1.0.0',
#     'category': 'Inventory',
#     'summary': 'Print custom product labels for GP-1125T thermal printer',
#     'author': 'Custom',
#     'depends': ['product', 'stock', 'web'],
#     'data': [
#         'security/ir.model.access.csv',
#         'wizard/product_label_wizard_views.xml',
#         'views/product_views.xml',
#     ],
#     'installable': True,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
{
    'name': 'Product Label Print - GP1125T',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Print custom product labels for GP-1125T thermal printer',
    'author': 'Custom',
    'depends': ['product', 'stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'report/product_label_report.xml',      # paper format + report action
        'report/product_label_template.xml',    # QWeb HTML template
        'wizard/product_label_wizard_views.xml',
        'views/product_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_label_print/static/src/css/label_print.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
