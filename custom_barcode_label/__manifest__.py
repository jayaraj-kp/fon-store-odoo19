{
    'name': 'Custom Barcode Label',
    'version': '19.0.3.0.0',
    'summary': 'Custom product barcode label with print quantity wizard and direct printer support',
    'author': 'Your Company',
    'category': 'Inventory',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_label_wizard_view.xml',
        'report/product_label_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
