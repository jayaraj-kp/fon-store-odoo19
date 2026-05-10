{
    'name': 'Product Label — Show MRP Price',
    'version': '19.0.1.0.0',
    'summary': 'Adds Show MRP Price checkbox to the standard Print Product Labels wizard',
    'author': 'Your Company',
    'category': 'Inventory',
    'depends': ['product_label_print'],
    'data': [
        'wizard/product_label_wizard_inherit.xml',
        'report/product_label_report_inherit.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}