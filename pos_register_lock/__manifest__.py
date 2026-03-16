# -*- coding: utf-8 -*-
{
    'name': 'POS Register Lock',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Lock POS register for manager review before closing',
    'description': """
POS Register Lock
=================
Adds a "Lock Register" button in the POS Closing Register popup.

Workflow:
1. Cashier clicks "Lock Register" in Closing Register popup
2. POS session is locked — cashier cannot sell or close
3. Manager logs into Odoo backend
4. Manager goes to Point of Sale > Sessions > opens the session
5. Manager clicks "Unlock Register" to allow cashier to proceed
6. Cashier can then close normally
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_session_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_register_lock/static/src/js/RegisterLock.js',
            'pos_register_lock/static/src/xml/RegisterLock.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
