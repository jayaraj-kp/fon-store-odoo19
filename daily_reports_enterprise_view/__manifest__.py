# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
{
    "name": "Daily Reports — Enterprise Interactive View (Cash Book, Bank Book, Day Book)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style interactive Cash Book, Bank Book, and Day Book reports with PDF and Excel export",
    "description": """
        Provides Enterprise-style interactive Daily Reports:
        - Cash Book (Cash journals & accounts with opening/closing balance)
        - Bank Book (Bank journals & accounts with opening/closing balance)
        - Day Book (All daily transactions across selected journals)
        - Interactive filters: Date range, Posted/Draft state, Partner, Analytic, Search
        - PDF export with header logo, footer, and bottom totals summary
        - Excel (XLSX) export with styled headers, journal/date groups, and totals
    """,
    "author": "Custom",
    "website": "",
    "depends": ["account", "web"],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/daily_reports_action.xml",
        "views/report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "daily_reports_enterprise_view/static/src/css/daily_reports_view.css",
            "daily_reports_enterprise_view/static/src/xml/daily_reports_view.xml",
            "daily_reports_enterprise_view/static/src/js/daily_reports_view.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
