{
    'name': 'POS Special Offers',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add time-based special offers to POS products and categories',
    'description': """
        Create special offers for POS with:
        - Product and category selection
        - Date range (From / To)
        - Active time setting
        - Percentage or fixed price discount
        - Offers button in POS top menu
    """,
    'author': 'Custom',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_special_offer_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_special_offers/static/src/css/special_offer.css',
            'pos_special_offers/static/src/xml/special_offer.xml',
            'pos_special_offers/static/src/js/SpecialOfferPopup.js',
            'pos_special_offers/static/src/js/SpecialOfferButton.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
