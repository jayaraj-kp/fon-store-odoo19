# -*- coding: utf-8 -*-
{
    'name': 'POS Register Lock',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Auto-lock POS register on close for manager excess/short review',
    'description': """
POS Register Lock
=================
Automatically locks the POS register when the cashier clicks "Close Register".
The closing amounts (cash counted, excess/short) are shown read-only to the cashier.
A manager must review and unlock from the Odoo backend before the cashier can close.

Workflow:
---------
1. Cashier clicks "Close Register" in the Closing Register popup.
2. The session is instantly locked in the backend (auto-lock).
3. The Closing Register popup becomes read-only — amounts are visible but cannot be changed.
4. A full-screen lock overlay prevents any other POS actions.
5. Manager logs into Odoo backend.
6. Manager goes to: Point of Sale → Sessions → opens this session.
7. Manager reviews the excess/short amounts shown in the session form.
8. Manager clicks "🔓 Unlock Register" (confirmed dialog).
9. POS polls every 5 seconds — overlay clears automatically when unlocked.
10. Cashier can now click "Close Register" again to complete the session close.
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
