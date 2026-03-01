{
    'name': 'POS Special Offers',
    'version': '19.0.3.0.0',
    'category': 'Point of Sale',
    'summary': 'Special offers with flat discount, coupon, purchase limit for POS',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_special_offer_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            # CSS first
            'pos_special_offers/static/src/css/special_offer.css',
            # JS must come BEFORE XML so components are defined before templates are compiled
            'pos_special_offers/static/src/js/special_offer_service.js',
            'pos_special_offers/static/src/js/special_offer_popup.js',
            'pos_special_offers/static/src/js/special_offer_button.js',
            # XML templates after JS
            'pos_special_offers/static/src/xml/SpecialOfferPopup.xml',
            'pos_special_offers/static/src/xml/SpecialOfferButton.xml',
            # NavbarPatch LAST - after all components are registered
            'pos_special_offers/static/src/xml/NavbarPatch.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
