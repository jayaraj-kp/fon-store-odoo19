{
    'name': 'Cash Book, Day Book, Bank Book Financial Reports (OWL)',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Interactive Cash Book, Day Book and Bank Book reports for Odoo 19 '
                '(works with Invoicing only, no Enterprise Accounting required)',
    'description': """
Cash Book, Day Book and Bank Book Reports
==========================================
Interactive, in-browser reports built with OWL:

* Live filter panel (dates, journals, accounts, target moves, sort, initial balance)
* Instant refresh without opening a wizard popup
* One click "Print PDF" for the classic printable report
* Works on Odoo 19 Community with only the `account` (Invoicing) app installed
""",
    'sequence': 10,
    'author': 'Odoo Mates',
    'license': 'LGPL-3',
    'company': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'website': 'https://www.odoomates.tech',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/om_daily_reports.xml',
        'views/account_daily_book_actions.xml',
        'report/reports.xml',
        'report/report_daybook.xml',
        'report/report_cashbook.xml',
        'report/report_bankbook.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'om_account_daily_reports/static/src/scss/account_daily_book_report.scss',
            'om_account_daily_reports/static/src/js/account_daily_book_report.js',
            'om_account_daily_reports/static/src/xml/account_daily_book_report.xml',
        ],
    },
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
}
