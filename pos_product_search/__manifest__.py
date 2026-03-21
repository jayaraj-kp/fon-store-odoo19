# -*- coding: utf-8 -*-
{
    'name': 'POS Product Search Filter',
    'version': '19.0.5.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Product search filter to POS Orders screen',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            # NO XML patch needed — Odoo 17/18/19 TicketScreen already loops
            # over getSearchFields() in its own template automatically.
            # Adding an XML patch that tries to find a <ul class="py-1">
            # causes: "Element cannot be located in element tree"
            'pos_product_search/static/src/js/ticket_screen_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}