# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
{
    "name": "Balance Sheet & P&L — Enterprise Interactive View",
    "version": "19.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style interactive Balance Sheet and Profit & Loss views",
    "description": """
        Provides Enterprise-style interactive financial statement views:
        - Balance Sheet with hierarchical expandable sections
        - Profit and Loss with subtotals (Gross Profit, Operating Income, Net Profit)
        - Sticky filter bar (date, comparison, posted entries, currency)
        - Unposted entries warning banner
        - PDF export
    """,
    "author": "Custom",
    "website": "",
    "depends": ["account", "web"],
    "data": [
        "views/financial_reports_action.xml",
        "views/report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "oca_financial_statements_enterprise_view/static/src/css/financial_reports_view.css",
            "oca_financial_statements_enterprise_view/static/src/xml/financial_reports_view.xml",
            "oca_financial_statements_enterprise_view/static/src/js/financial_reports_view.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
