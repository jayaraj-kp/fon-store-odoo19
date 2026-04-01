# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Analytic Account',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Configuration',
    'summary': 'Link Analytic Account to Warehouse; auto-apply on bills/journal entries',
    'description': """
        - Adds an Analytic Account field on each Warehouse (stock.warehouse).
        - When a user whose default warehouse has an analytic account creates/confirms
          a vendor bill (account.move), the analytic account is automatically applied
          to every invoice line that has an account configured.
        - The same analytic account is stamped on outgoing stock moves / pickings
          that originate from that warehouse.
        - A server action lets you retroactively apply the analytic account to
          existing draft bills for a warehouse.
    """,
    'author': 'Custom',
    'depends': [
        'stock',
        'purchase',
        'account',
        'analytic',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
