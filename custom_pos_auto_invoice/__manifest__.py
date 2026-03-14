{
    'name': 'POS Auto Invoice on Payment',
    'version': '19.0.2.0.0',
    'summary': 'Automatically create invoice for every POS payment (including one-click fast payment)',
    'description': """
        Auto-Invoice POS Orders
        =======================
        • Sets to_invoice = True automatically for ALL payment types.
        • Works with Cash, Card, and one-click fast payment buttons.
        • Only invoices orders that have a customer set (Odoo requirement).
        • Patches OrderPaymentValidation directly — the single class used
          by BOTH the Payment Screen AND the fast payment shortcut.
        • Server-side safety net also enforces invoice flag via model override.
    """,
    'category': 'Point of Sale',
    'author': 'FON Store',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'custom_pos_auto_invoice/static/src/js/auto_invoice.js',
            'custom_pos_auto_invoice/static/src/xml/auto_invoice.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
