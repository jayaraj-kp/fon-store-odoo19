# # -*- coding: utf-8 -*-
# {
#     'name': 'POS Product Search Filter',
#     'version': '19.0.5.0.0',
#     'category': 'Point of Sale',
#     'summary': 'Add Product search filter to POS Orders screen',
#     'author': 'Custom',
#     'depends': ['point_of_sale'],
#     'assets': {
#         'point_of_sale._assets_pos': [
#             # NO XML patch needed — Odoo 17/18/19 TicketScreen already loops
#             # over getSearchFields() in its own template automatically.
#             # Adding an XML patch that tries to find a <ul class="py-1">
#             # causes: "Element cannot be located in element tree"
#             'pos_product_search/static/src/js/ticket_screen_patch.js',
#         ],
#     },
#     'installable': True,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }

# -*- coding: utf-8 -*-
{
    'name': 'POS Product Search Filter',
    'version': '19.0.6.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Product, Payment Method, Category, Mobile, Amount, Custom Filter to POS',
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        # 'views/pos_order_search_view.xml',  # Enable after finding correct inherit_id
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_product_search/static/src/xml/custom_filter_popup.xml',
            'pos_product_search/static/src/js/ticket_screen_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}