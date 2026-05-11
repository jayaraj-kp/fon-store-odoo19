#
# {
#     'name': 'Product Label Print - GP1125T',
#     'version': '19.0.1.0.0',
#     'category': 'Inventory',
#     'summary': 'Print custom product labels for GP-1125T thermal printer',
#     'author': 'Custom',
#     'depends': ['product', 'stock', 'web'],
#     'data': [
#         'security/ir.model.access.csv',
#         'report/product_label_report.xml',
#         'report/product_label_template.xml',
#         'wizard/product_label_wizard_views.xml',
#         'views/product_views.xml',
#     ],
#     'assets': {
#         'web.assets_backend': [
#             'product_label_print/static/src/css/label_print.css',
#             'product_label_print/static/src/css/label_print_dialog.css',
#             'product_label_print/static/src/xml/product_label_print_dialog.xml',
#             'product_label_print/static/src/js/product_label_print_dialog.js',
#         ],
#     },
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
    # ── FIX: added your MRP module name so mrp_price field is available ──────
    # Replace 'product_mrp_model' below with the actual folder/technical name
    # of your first module (the one that adds the mrp_price field).
    'depends': ['product', 'stock', 'web', 'product_model_field'],
    # ─────────────────────────────────────────────────────────────────────────
    'data': [
        'security/ir.model.access.csv',
        'report/product_label_report.xml',
        'report/product_label_template.xml',
        'wizard/product_label_wizard_views.xml',
        'views/product_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_label_print/static/src/css/label_print.css',
            'product_label_print/static/src/css/label_print_dialog.css',
            'product_label_print/static/src/xml/product_label_print_dialog.xml',
            'product_label_print/static/src/js/product_label_print_dialog.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}