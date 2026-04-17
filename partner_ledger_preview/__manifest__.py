{
    'name': 'Partner Ledger Preview',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Adds an inline HTML preview to the Partner Ledger wizard',
    'description': """
        Extends the accounting_pdf_reports Partner Ledger wizard
        with a Preview button that renders an HTML preview of the
        report without generating a PDF.
    """,
    'author': 'Custom',
    'depends': ['accounting_pdf_reports'],
    'data': [
        'wizard/partner_ledger_preview_view.xml',
        'wizard/partner_ledger_wizard_inherit.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
