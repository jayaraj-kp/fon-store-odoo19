{
    'name': 'Custom Barcode Label',
    'version': '19.0.3.0.0',
    'summary': 'Custom product barcode label: logo, name, barcode, MRP, Instagram QR — with quantity copies wizard',
    'author': 'Your Company',
    'category': 'Inventory',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/print_label_wizard.xml',
        'report/product_label_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
