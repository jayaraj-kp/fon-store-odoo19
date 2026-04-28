{
    'name': 'Product Model Field & MRP Price',
    'version': '19.0.2.0.0',
    'category': 'Sales',
    'summary': 'Add Model and MRP Price fields to Product with Excel Import/Export',
    'description': """
        This module adds two custom fields to the Product master:

        * **Model** – alphanumeric model identifier (e.g. IP14PM)
        * **MRP Price** – Maximum Retail Price (monetary field)

        Both fields appear in:
        - Product form view (General Information tab)
        - Product list / tree view (optional columns)
        - Product search view (searchable)

        An Import / Export wizard is available under
        Inventory › Configuration › Import / Export Products.
        The wizard supports:
        - Export all products to Excel (including Model & MRP Price)
        - Download a pre-formatted import template
        - Import products from Excel (create new or update existing)
    """,
    'author': 'Your Company Name',
    'website': 'https://yourcompany.com',
    'depends': ['product', 'sale', 'stock'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/product_views.xml',
        'views/product_import_export_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
    'external_dependencies': {
        'python': ['openpyxl'],
    },
}
