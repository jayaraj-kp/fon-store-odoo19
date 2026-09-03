# # Copyright 2024 Custom Development
# # License: LGPL-3.0 or later
# {
#     "name": "Partner Ledger — Enterprise Interactive View",
#     "version": "19.0.1.0.0",
#     "category": "Accounting/Reporting",
#     "summary": "Enterprise-style interactive Partner Ledger report",
#     "description": """
#         Provides an Enterprise-style interactive Partner Ledger report:
#         - Grouped by partner, with expandable journal items
#         - Running balance per partner
#         - Filters: date/fiscal year, account type (Trade Partners),
#           partners, partner tags, posted/draft entries, search
#         - PDF export
#     """,
#     "author": "Custom",
#     "website": "",
#     "depends": ["account", "web"],
#     "data": [
#         "security/ir.model.access.csv",
#         "views/partner_ledger_action.xml",
#         "views/report_templates.xml",
#     ],
#     "assets": {
#         "web.assets_backend": [
#             "partner_ledger_enterprise_view/static/src/img/header.png",
#             "partner_ledger_enterprise_view/static/src/css/partner_ledger_view.css",
#             "partner_ledger_enterprise_view/static/src/xml/partner_ledger_view.xml",
#             "partner_ledger_enterprise_view/static/src/js/partner_ledger_view.esm.js",
#         ],
#     },
#     "installable": True,
#     "application": False,
#     "auto_install": False,
#     "license": "LGPL-3",
# }
# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
{
    "name": "Partner Ledger & Aged Receivable & Aged Payable — Enterprise Interactive View",
    "version": "19.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style interactive Partner Ledger, Aged Receivable and Aged Payable reports",
    "description": """
        Provides Enterprise-style interactive accounting reports:
        - Partner Ledger: grouped by partner, expandable journal items, running balance
        - Aged Receivable: aging buckets (1-30, 31-60, 61-90, 91-120, Older)
        - Aged Payable: aging buckets for supplier liabilities
        - Filters: date, account type, partners, partner tags, posted/draft entries
        - PDF and Excel export
    """,
    "author": "Custom",
    "website": "",
    "depends": ["account", "web", "sale", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/partner_ledger_action.xml",
        "views/aged_receivable_action.xml",
        "views/aged_payable_action.xml",
        "views/partner_ledger_fields_views.xml",
        "views/report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "partner_ledger_enterprise_view/static/src/css/partner_ledger_view.css",
            "partner_ledger_enterprise_view/static/src/xml/partner_ledger_view.xml",
            "partner_ledger_enterprise_view/static/src/xml/aged_receivable_view.xml",
            "partner_ledger_enterprise_view/static/src/xml/aged_payable_view.xml",
            "partner_ledger_enterprise_view/static/src/js/partner_ledger_view.esm.js",
            "partner_ledger_enterprise_view/static/src/js/aged_receivable_view.esm.js",
            "partner_ledger_enterprise_view/static/src/js/aged_payable_view.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}