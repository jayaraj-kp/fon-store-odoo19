# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PrintLabelWizard(models.TransientModel):
    _name = 'custom_barcode_label.print_wizard'
    _description = 'Print Barcode Labels Wizard'

    label_qty = fields.Integer(
        string='Copies per Label',
        default=1,
        required=True,
    )

    def action_get_pdf_url(self):
        """
        Returns the PDF report URL so the JS dialog can open it in an
        iframe and trigger window.print() — exactly like the POS receipt flow.
        """
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        qty = max(1, self.label_qty)

        if active_model == 'product.template':
            products = self.env['product.template'].browse(active_ids).mapped(
                'product_variant_ids'
            )
            report_name = 'custom_barcode_label.action_report_custom_label_tmpl'
        else:
            products = self.env['product.product'].browse(active_ids)
            report_name = 'custom_barcode_label.action_report_custom_label'

        label_qty_map = {str(p.id): qty for p in products}

        # Build the PDF URL using Odoo's report route
        report = self.env.ref(report_name)
        ids_str = ','.join(str(i) for i in products.ids)

        # Encode data as query-safe format
        import json, urllib.parse
        data_encoded = urllib.parse.quote(json.dumps({'label_qty': label_qty_map}))

        pdf_url = (
            f'/report/pdf/{report.report_name}/{ids_str}'
            f'?data={data_encoded}'
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'custom_barcode_label.print_dialog',
            'params': {
                'pdf_url': pdf_url,
                'label_qty': qty,
                'product_count': len(products),
            },
        }

    def action_download_pdf(self):
        """Fallback: download PDF directly (no printer dialog)."""
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        qty = max(1, self.label_qty)

        if active_model == 'product.template':
            products = self.env['product.template'].browse(active_ids).mapped(
                'product_variant_ids'
            )
            report_ref = 'custom_barcode_label.action_report_custom_label_tmpl'
        else:
            products = self.env['product.product'].browse(active_ids)
            report_ref = 'custom_barcode_label.action_report_custom_label'

        label_qty_map = {str(p.id): qty for p in products}

        return self.env.ref(report_ref).report_action(
            products.ids,
            data={'label_qty': label_qty_map},
        )
