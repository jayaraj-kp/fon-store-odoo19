{
    "name": "POS Cash Customer Contact",
    "version": "3.0",
    "depends": ["point_of_sale", "contacts"],
    "data": [
        "views/res_partner_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_cash_customer_contact/static/src/css/phone_customer_bar.css",
            "pos_cash_customer_contact/static/src/js/phone_customer_bar.js",
            "pos_cash_customer_contact/static/src/xml/phone_customer_bar.xml",
        ],
    },
    "installable": True,
}