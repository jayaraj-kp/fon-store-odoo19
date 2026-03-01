{
    'name': 'POS Special Offers',
    'version': '19.0.2.0.0',
    'category': 'Point of Sale',
    'summary': 'Special offers with flat discount, coupon, purchase limit for POS',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_special_offer_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_special_offers/static/src/css/special_offer.css',
            'pos_special_offers/static/src/xml/SpecialOfferPopup.xml',
            'pos_special_offers/static/src/xml/SpecialOfferButton.xml',
            'pos_special_offers/static/src/xml/NavbarPatch.xml',
            'pos_special_offers/static/src/js/special_offer_service.js',
            'pos_special_offers/static/src/js/special_offer_popup.js',
            'pos_special_offers/static/src/js/special_offer_button.js',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
