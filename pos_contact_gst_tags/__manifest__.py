{
    'name': 'POS Partner GSTIN & Tags',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add GSTIN (VAT) and Tags fields to POS Create Contact wizard',
    'description': """
        Extends the POS Create Contact wizard to include:
        - GSTIN / Tax ID (vat) field
        - Contact Tags (category_id) field
        Works without the Accounting module installed.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}