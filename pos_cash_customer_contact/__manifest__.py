{
    "name": "POS Cash Customer Contact",
    "version": "1.0",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_cash_customer_contact/static/src/js/customer_popup.js",
            "pos_cash_customer_contact/static/src/js/customer_search.js",
            "pos_cash_customer_contact/static/src/js/payment_patch.js",
            "pos_cash_customer_contact/static/src/xml/customer_popup.xml",
        ],
    },
    "installable": True,
}