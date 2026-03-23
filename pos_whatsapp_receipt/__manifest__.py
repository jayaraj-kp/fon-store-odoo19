{
    'name': 'POS WhatsApp Receipt',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Send POS receipts automatically via WhatsApp after transaction',
    'author': 'Custom',
    'depends': ['point_of_sale', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/pos_whatsapp_log_views.xml',
        'data/ir_sequence_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_whatsapp_receipt/static/src/js/whatsapp_button.js',
            'pos_whatsapp_receipt/static/src/js/whatsapp_button.xml',
            'pos_whatsapp_receipt/static/src/css/whatsapp.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
