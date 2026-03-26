# -*- coding: utf-8 -*-
{
    'name': 'Sales Contacts Menu & POS Cash Customer Report',
    'version': '19.0.3.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Contacts menu under Sales > Orders + POS Cash Customer Report',
    'description': """
        - Adds "Contacts" menu under Sales > Orders
        - Lists all contacts created under CASH CUSTOMER parent
        - Provides a detailed PDF report of POS sales per cash customer
        - Report includes: customer name, phone, orders, amounts, dates, totals
    """,
    'author': 'Custom',
    'depends': ['sale_management', 'contacts', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cash_customer_report_wizard_view.xml',
        'report/cash_customer_report_template.xml',
        'report/cash_customer_report_action.xml',
        'views/sales_contacts_menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
