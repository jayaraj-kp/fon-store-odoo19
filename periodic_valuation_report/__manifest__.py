{
    'name': 'Periodic Inventory Valuation Report',
    'version': '1.0',
    'depends': ['stock', 'purchase', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_view.xml',
    ],
    'installable': True,
    'application': True,
}