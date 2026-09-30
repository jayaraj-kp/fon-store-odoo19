{
    'name': 'Hide Product Cost',
    'version': '19.0.1.0.0',
    'category': 'Sales/Products',
    'summary': 'Hide the product Cost field from selected users',
    'description': """
Hide Product Cost
=================
Adds a "Product Cost" privilege on the user form (Visible / Hidden).
Users set to "Hidden" no longer see the Cost field on product forms and lists.
Everyone else keeps the standard behaviour. No Python code, no new models,
no overrides: zero impact on performance and on other features.
    """,
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'security/security.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
}
