# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductLabelPrintWizard(models.TransientModel):
    _name = 'product.label.print.wizard'
    _description = 'Print Product Labels Wizard'

    qty = fields.Integer(
        string='Number of Copies per Product',
        default=1,
        required=True,
        help='How many copies of each label to print.'
    )
    printer_name = fields.Char(
        string='Printer Name (optional)',
        help='Leave blank to use the default printer. '
             'Enter exact printer name as shown in your OS print dialog.'
    )

    @api.constrains('qty')
    def _check_qty(self):
        for rec in self:
            if rec.qty < 1:
                raise UserError(_('Number of copies must be at least 1.'))
            if rec.qty > 500:
                raise UserError(_('Maximum 500 copies allowed per print job.'))

    def action_print_pdf(self):
        """Print as PDF (standard Odoo report — opens browser print dialog)."""
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        data = {'qty': self.qty}

        if active_model == 'product.template':
            report_ref = 'custom_barcode_label.action_report_custom_label_tmpl'
            records = self.env['product.template'].browse(active_ids)
        else:
            report_ref = 'custom_barcode_label.action_report_custom_label'
            records = self.env['product.product'].browse(active_ids)

        return self.env.ref(report_ref).report_action(records, data=data)

    def action_print_direct(self):
        """
        Direct print: generates PDF and sends it to the named printer via CUPS/lp.
        Requires the Odoo server to have CUPS installed and the printer configured.
        Falls back to normal PDF if printing fails.
        """
        import subprocess
        import tempfile
        import os

        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        data = {'qty': self.qty}

        if active_model == 'product.template':
            report_ref = 'custom_barcode_label.action_report_custom_label_tmpl'
            records = self.env['product.template'].browse(active_ids)
        else:
            report_ref = 'custom_barcode_label.action_report_custom_label'
            records = self.env['product.product'].browse(active_ids)

        # Generate PDF bytes
        report = self.env.ref(report_ref)
        pdf_content, _ = report._render_qweb_pdf(records.ids, data=data)

        # Write to temp file and send to printer
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_content)
                tmp_path = tmp.name

            printer = self.printer_name.strip() if self.printer_name else ''
            cmd = ['lp']
            if printer:
                cmd += ['-d', printer]
            cmd.append(tmp_path)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            os.unlink(tmp_path)

            if result.returncode != 0:
                raise UserError(
                    _('Printer error: %s\n\nTip: Make sure CUPS is installed and the '
                      'printer name is correct.') % result.stderr
                )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Print Job Sent'),
                    'message': _('%d label(s) sent to printer successfully.') % (
                        len(records) * self.qty
                    ),
                    'type': 'success',
                    'sticky': False,
                },
            }
        except FileNotFoundError:
            # lp not found — fall back to PDF download
            return report.report_action(records, data=data)
        except subprocess.TimeoutExpired:
            raise UserError(_('Printer timed out. Please check printer connection.'))
