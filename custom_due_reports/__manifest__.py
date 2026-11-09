{
    'name': 'Customer & Vendor Due Reports',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'Customer Due Report and Vendor (Supplier) Due Report with overdue/remaining day tracking',
    'description': """
Customer & Vendor Due Reports
==============================
Adds two report wizards under Accounting > Reporting > Due Reports:

* **Customer Due Report** – outstanding customer invoices with ageing.
* **Vendor Due Report** – outstanding vendor bills with ageing.

Each report shows, per document: Sl No, Voucher/Invoice No, Date, Party
Name (customer report), Due Day, Due Date, Remaining/Overdue Days, Bill
Amount, Paid, Balance, Total Amount, Salesman & L.P.O (customer report)
or Vendor Invoice Number (vendor report) - laid out to match the classic
"Supplier/Customer Due Report" format.
    """,
    'author': 'Your Company',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['account', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'report/due_report_templates.xml',
        'report/due_report_actions.xml',
        'views/due_report_line_views.xml',
        'views/due_report_wizard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_due_reports/static/src/css/due_report_view.css',
            'custom_due_reports/static/src/xml/due_report_view.xml',
            'custom_due_reports/static/src/js/due_report_view.esm.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}

