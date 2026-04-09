{
    'name': 'Product Model Field',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add alphanumeric Model field to Product',
    'description': """
        This module adds a custom alphanumeric 'Model' field to the Product master.
        The field is visible in the product creation/edit form and can be exported to Excel.
    """,
    'author': 'Your Company Name',
    'website': 'https://yourcompany.com',
    'depends': ['product', 'sale'],
    'data': [
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}