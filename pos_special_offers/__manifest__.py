{
    'name': 'POS Special Offers',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add time-based special offers to POS products and categories',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_special_offer_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_special_offers/static/src/css/special_offer.css',
            'pos_special_offers/static/src/js/SpecialOfferService.js',
            'pos_special_offers/static/src/js/SpecialOfferPopup.js',
            'pos_special_offers/static/src/js/SpecialOfferButton.js',
            'pos_special_offers/static/src/xml/SpecialOfferPopup.xml',
            'pos_special_offers/static/src/xml/SpecialOfferButton.xml',
            'pos_special_offers/static/src/xml/NavbarPatch.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
