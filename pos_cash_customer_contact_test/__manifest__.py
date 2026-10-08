# {
#     "name": "POS Cash Customer Contact (Test)",
#     "version": "2.0",
#     "depends": ["point_of_sale"],
#     "assets": {
#         "point_of_sale._assets_pos": [
#             "pos_cash_customer_contact_test/static/src/css/phone_customer_bar.css",
#             "pos_cash_customer_contact_test/static/src/js/phone_customer_bar.js",
#             "pos_cash_customer_contact_test/static/src/xml/phone_customer_bar.xml",
#         ],
#     },
#     "installable": True,
# }

{
    "name": "POS Cash Customer Contact (Test)",
    "version": "2.0",
    "depends": ["point_of_sale", "partner_gender"],
    "data": ["views/res_partner_views.xml"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_cash_customer_contact_test/static/src/css/phone_customer_bar.css",
            "pos_cash_customer_contact_test/static/src/js/phone_customer_bar.js",
            "pos_cash_customer_contact_test/static/src/xml/phone_customer_bar.xml",
        ],
    },
    "installable": True,
}