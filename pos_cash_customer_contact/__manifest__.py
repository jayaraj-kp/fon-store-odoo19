{
    "name": "POS Quick Cash Customer",
    "version": "1.0",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale.assets": [
            "pos_quick_cash_customer/static/src/js/*.js",
            "pos_quick_cash_customer/static/src/xml/*.xml",
        ],
    },
    "installable": True,
}