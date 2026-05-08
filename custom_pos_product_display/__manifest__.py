{
    'name': 'POS Product Display - Remove Internal Reference',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Remove internal reference codes from POS product display',
    'author': 'Custom Development',
    'depends': ['point_of_sale', 'product'],
    'data': [],
    'installable': True,
    'application': False,
    'assets': {
        'point_of_sale.assets_js': [
            'custom_pos_product_display/static/src/js/product_display.js',
        ],
    },
    'images': ['static/description/icon.png'],
}
