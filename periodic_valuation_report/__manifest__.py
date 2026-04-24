{
    'name': 'Periodic Inventory Valuation Report',
    'version': '1.0',
    'depends': ['stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_view.xml',
    ],
    # ADD THIS LINE:
    'installable': True,
    'application': True,
}
