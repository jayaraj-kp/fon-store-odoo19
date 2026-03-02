{
    'name': 'POS Special Offers',
    'version': '19.0.5.0.0',
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
            # Service first (no deps)
            'pos_special_offers/static/src/js/special_offer_service.js',
            # Popup (no POS deps)
            'pos_special_offers/static/src/js/special_offer_popup.js',
            # Button (patches Navbar)
            'pos_special_offers/static/src/js/special_offer_button.js',
            # Auto-apply (patches PosOrder)
            'pos_special_offers/static/src/js/special_offer_auto_apply.js',
            # XML templates
            'pos_special_offers/static/src/xml/SpecialOfferPopup.xml',
            'pos_special_offers/static/src/xml/SpecialOfferButton.xml',
            'pos_special_offers/static/src/xml/NavbarPatch.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
