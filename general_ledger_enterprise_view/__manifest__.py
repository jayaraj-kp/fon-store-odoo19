# Copyright 2024 Custom Development
# License: LGPL-3.0 or later
{
    "name": "General Ledger & Trial Balance — Enterprise Interactive View",
    "version": "19.0.1.0.0",
    "category": "Accounting/Reporting",
    "summary": "Enterprise-style OWL-powered interactive General Ledger & Trial Balance for Odoo 19 CE",
    "description": """
        Standalone Enterprise-style General Ledger & Trial Balance:
        - Inline sticky filter bar (date range, journals, target moves, hide zero)
        - Expandable account rows with move lines inline
        - PDF / XLSX export (standalone, zero external module dependencies)
        - Powered by OWL JS
        - Works out-of-the-box with Odoo 19 CE Invoicing (account, web)
    """,
    "author": "Custom",
    "website": "",
    "depends": ["account", "web"],
    "external_dependencies": {
        "python": ["xlsxwriter"],
    },
    "data": [
        "security/ir.model.access.csv",
        "security/gl_export_job_security.xml",
        "views/general_ledger_action.xml",
        "views/report_templates.xml",
        "views/gl_export_job_views.xml",
        "data/gl_export_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "general_ledger_enterprise_view/static/src/css/general_ledger_view.css",
            "general_ledger_enterprise_view/static/src/xml/general_ledger_view.xml",
            "general_ledger_enterprise_view/static/src/js/general_ledger_view.esm.js",
        ],
    },
    "pre_init_hook": "pre_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}