# -*- coding: utf-8 -*-
{
    'name': 'POS Customer Unique ID',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Auto-generate shop-specific unique customer IDs from POS (e.g. CHL-00001, KON-00001)',
    'description': """
        This module adds a unique sequential customer ID to contacts created
        from Point of Sale. Each shop has a custom prefix code:
        - Chelari shop  → CHL - 00001, CHL - 00002 ...
        - Kondotty shop → KON - 00001, KON - 00002 ...

        Features:
        - Configure shop code per POS terminal (Settings > Point of Sale)
        - Auto-generate ID on new contact creation from POS
        - ID is visible in POS customer form and backend partner form
        - Sequence uses no-gap numbering per shop
        - Reset/configure sequence from POS settings
    """,
    'author': 'Custom Development',
    'depends': ['point_of_sale', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_customer_unique_id/static/src/js/partner_editor_patch.js',
            'pos_customer_unique_id/static/src/xml/partner_editor_patch.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
