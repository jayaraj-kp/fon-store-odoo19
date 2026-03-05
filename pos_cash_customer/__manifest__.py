# -*- coding: utf-8 -*-
{
    'name': 'POS Cash Customer',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Create contacts under a master CASH CUSTOMER in POS',
    'description': """
        This module adds the following features to Odoo 19 CE POS:
        - Automatically creates a master "CASH CUSTOMER" contact on installation
        - When creating a new customer in POS, the form shows a "Parent" field
          pre-filled with "CASH CUSTOMER"
        - All new POS customers are saved as contacts (children) under CASH CUSTOMER
        - The POS customer button opens a creation form with the parent pre-set
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/cash_customer_data.xml',
        'views/res_partner_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_cash_customer/static/src/js/CashCustomerButton.js',
            'pos_cash_customer/static/src/js/CreateCustomerForm.js',
            'pos_cash_customer/static/src/js/PosStore.js',
            'pos_cash_customer/static/src/xml/CashCustomerButton.xml',
            'pos_cash_customer/static/src/xml/CreateCustomerForm.xml',
            'pos_cash_customer/static/src/css/pos_cash_customer.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
