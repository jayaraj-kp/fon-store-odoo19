{
    'name': 'Perpetual Inventory Valuation (Odoo 19 CE)',
    'version': '19.0.1.0.0',
    'summary': 'Restores real-time accounting entries for stock moves in Odoo 19 CE',
    'category': 'Inventory/Accounting',
    'author': 'Your Name',
    'depends': ['stock', 'account'],
    'data': [
        'views/stock_valuation_views.xml', # Load the XML here
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}