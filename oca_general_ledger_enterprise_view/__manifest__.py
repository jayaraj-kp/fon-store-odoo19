# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
{
    "name": "General Ledger — Enterprise Interactive View",
    "version": "19.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style OWL-powered interactive General Ledger view for OCA",
    "description": """
        Transforms the OCA account_financial_report General Ledger into an
        Enterprise-style interactive view with:
        - Inline sticky filter bar (date range, journals, target moves, hide zero)
        - Expandable account rows with move lines inline
        - PDF / XLSX export via OCA's existing report infrastructure
        - Powered by OWL JS
    """,
    "author": "Custom",
    "website": "",
    "depends": ["account_financial_report", "web"],
    "data": [
        "views/general_ledger_action.xml",
        "views/report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "oca_general_ledger_enterprise_view/static/src/css/general_ledger_view.css",
            "oca_general_ledger_enterprise_view/static/src/xml/general_ledger_view.xml",
            "oca_general_ledger_enterprise_view/static/src/js/general_ledger_view.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
