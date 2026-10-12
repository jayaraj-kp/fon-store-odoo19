# Copyright 2024 YourCompany
# License: LGPL-3.0 or later
{
    "name": "Balance Sheet, P&L & VAT — Enterprise Interactive View",
    "version": "19.0.1.1.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style interactive Balance Sheet, Profit & Loss and VAT Return views for Odoo Community",
    "description": """
        Provides Enterprise-style interactive financial statement views for Odoo Community Edition:

        Balance Sheet
        =============
        - Hierarchical expandable sections (Assets, Liabilities, Equity)
        - Current Year / Previous Years Unallocated Earnings (auto-computed)
        - Drill-down into journal items from any account line
        - Split Horizontally layout

        Profit & Loss
        =============
        - Gross Profit, Operating Income, Net Profit subtotals
        - Cost of Revenue, Operating Expenses, Other Income breakdown

        VAT Return (Saudi Arabia)
        =========================
        - 16-line GAZT-style VAT return
        - Standard / Reduced / Zero-rated / Export / Exempt buckets
        - Reverse charge and customs import lines

        Common Features
        ===============
        - Sticky filter bar (Date: Month / Quarter / Year / Custom)
        - Comparison: Previous Period / Same Period Last Year / Specific Date (multi-period)
        - Analytic Account filter (per-company)
        - Posted / Draft entries toggle
        - Unposted entries warning banner
        - Debit & Credit columns
        - Hide Lines at 0 / Unfold All
        - PDF and Excel export
        - Arabic / RTL layout support
    """,
    "author": "YourCompany",
    "website": "https://yourwebsite.com",
    "depends": ["account", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/financial_reports_action.xml",
        "views/report_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "financial_statements_enterprise_view/static/src/css/financial_reports_view.css",
            "financial_statements_enterprise_view/static/src/xml/financial_reports_view.xml",
            "financial_statements_enterprise_view/static/src/js/financial_reports_view.esm.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}