# -*- coding: utf-8 -*-
from odoo import models


def _due_report_values(env, docids, data):
    """Shared by the customer and vendor parsers.

    The wizard decides which currency every partner is printed in
    (partner's transaction currency by default, or the currency chosen in
    the on-screen Currency filter which arrives in data['currency_opts']).
    """
    data = data or {}
    wizard = env['due.report.wizard'].browse(data['wizard_id'])
    values = wizard._get_pdf_render_values(data.get('currency_opts') or False)
    values.update({
        'doc_ids': docids,
        'doc_model': 'due.report.wizard',
        'docs': wizard,
    })
    return values


class CustomerDueReportParser(models.AbstractModel):
    _name = 'report.custom_due_reports.report_customer_due_document'
    _description = 'Customer Due Report Parser'

    def _get_report_values(self, docids, data=None):
        return _due_report_values(self.env, docids, data)


class VendorDueReportParser(models.AbstractModel):
    _name = 'report.custom_due_reports.report_vendor_due_document'
    _description = 'Vendor Due Report Parser'

    def _get_report_values(self, docids, data=None):
        return _due_report_values(self.env, docids, data)