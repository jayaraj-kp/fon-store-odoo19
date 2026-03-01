{
    'name': 'POS Direct Partner Create',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Open Create Contact wizard directly from POS',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_partner_create/static/src/js/partner_create_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}