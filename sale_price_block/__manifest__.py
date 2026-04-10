{
    'name': 'Block Sale Below Cost Price',
    'version': '19.0.1.0.0',
    'summary': 'Blocks sale order confirmation when unit price is below product cost price',
    'description': """
        This module prevents confirming a sale order if any order line
        has a unit price lower than the product's cost price (standard_price).
        The error message is shown only when the user clicks the Confirm button.
    """,
    'category': 'Sales/Sales',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
