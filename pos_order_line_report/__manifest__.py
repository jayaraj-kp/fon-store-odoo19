# -*- coding: utf-8 -*-
{
    'name': 'POS Order Line Report (Margin & Product Pivot)',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Adds product-wise margin pivot report for POS in Community Edition',
    'description': """
        This module adds a dedicated pivot/graph/list analysis view
        on POS Order Lines, showing:
        - Product & Product Category grouping
        - Quantity Sold
        - Revenue (price subtotal)
        - Cost (standard price × qty)
        - Gross Margin (revenue - cost)
        - Margin % 
        Works fully on Odoo 19 Community Edition.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_order_line_report_views.xml',
        'views/pos_order_line_report_menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
