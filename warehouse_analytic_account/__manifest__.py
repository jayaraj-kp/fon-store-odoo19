# # -*- coding: utf-8 -*-
# {
#     'name': 'Warehouse Analytic Account',
#     'version': '19.0.2.0.0',
#     'category': 'Inventory/Configuration',
#     'summary': 'Auto-apply warehouse analytic account on sales, purchases and invoices',
#     'description': """
#         Adds an Analytic Account field on each Warehouse.
#         When a user whose default warehouse has an analytic account creates any of
#         the following documents, the analytic account is automatically applied
#         to all order/invoice lines:
#
#         - Sales Quotation & Sales Order
#         - Purchase Quotation (RFQ) & Purchase Order
#         - Customer Invoice & Credit Note
#         - Vendor Bill & Vendor Refund
#         - Stock moves / pickings (on validation)
#     """,
#     'author': 'Custom',
#     'depends': [
#         'stock',
#         'purchase',
#         'sale',
#         'account',
#         'analytic',
#     ],
#     'data': [
#         'security/ir.model.access.csv',
#         'views/stock_warehouse_views.xml',
#         'views/res_users_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
# -*- coding: utf-8 -*-
{
    'name': 'Warehouse Analytic Account',
    'version': '19.0.3.0.0',
    'category': 'Inventory/Configuration',
    'summary': 'Auto-apply warehouse analytic account on sales, purchases, invoices and POS orders',
    'description': """
        Adds an Analytic Account field on each Warehouse.
        When a user whose default warehouse has an analytic account creates any of
        the following documents, the analytic account is automatically applied
        to all order/invoice lines:

        - Sales Quotation & Sales Order
        - Purchase Quotation (RFQ) & Purchase Order
        - Customer Invoice & Credit Note
        - Vendor Bill & Vendor Refund
        - Stock moves / pickings (on validation)
        - POS Orders & POS Order Lines (NEW)
    """,
    'author': 'Custom',
    'depends': [
        'stock',
        'purchase',
        'sale',
        'account',
        'analytic',
        'point_of_sale',  # Added POS dependency
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_warehouse_views.xml',
        'views/res_users_views.xml',
        # 'views/pos_order_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
