{
    'name': 'POS Partner GSTIN & Tags',
    'version': '19.0.1.0.0',
    'summary': 'Add GSTIN and Tags fields to POS Customer Form',
    'category': 'Point of Sale',
    'author': 'Your Name',
    'depends': ['point_of_sale', 'base'],
    'data': [
        'views/pos_partner_form_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_partner_fields/static/src/cash_move_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
