{
    'name': 'POS Special Offers',
    'version': '19.0.4.0.0',
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
            # JS loaded in dependency order:
            # 1. Service (no POS deps)
            # 2. Popup (no POS deps)
            # 3. Button (imports Navbar + usePos + Popup, patches Navbar)
            'pos_special_offers/static/src/js/special_offer_service.js',
            'pos_special_offers/static/src/js/special_offer_popup.js',
            'pos_special_offers/static/src/js/special_offer_button.js',
            # XML templates
            'pos_special_offers/static/src/xml/SpecialOfferPopup.xml',
            'pos_special_offers/static/src/xml/SpecialOfferButton.xml',
            # NavbarPatch last - after Navbar is patched with SpecialOfferButton
            'pos_special_offers/static/src/xml/NavbarPatch.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
