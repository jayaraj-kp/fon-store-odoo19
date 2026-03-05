# -*- coding: utf-8 -*-
import json
from odoo import models, fields, api


class PrintLabelWizard(models.TransientModel):
    _name = 'custom_barcode_label.print_wizard'
    _description = 'Print Barcode Labels Wizard'

    label_qty = fields.Integer(
        string='Copies per Label',
        default=1,
        required=True,
    )

    def action_print_labels(self):
        """
        1. Save qty to ir.config_parameter (report reads it directly)
        2. Return ir.actions.report with report_type=qweb-pdf
           → Odoo opens the same Print Preview dialog as invoices
        """
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        qty = max(1, self.label_qty)

        if active_model == 'product.template':
            products = (
                self.env['product.template']
                .browse(active_ids)
                .mapped('product_variant_ids')
            )
            report_name = 'custom_barcode_label.report_custom_label_tmpl_document'
        else:
            products = self.env['product.product'].browse(active_ids)
            report_name = 'custom_barcode_label.report_custom_label_document'

        # Save qty map to system parameter — report reads this directly
        label_qty_map = {str(p.id): qty for p in products}
        self.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_qty',
            json.dumps(label_qty_map)
        )

        # Build IDs string for the report URL
        ids_str = ','.join(str(i) for i in products.ids)

        # Return the same action structure Odoo uses for invoice printing
        # This triggers the Print Preview dialog (with printer selector)
        return {
            'type': 'ir.actions.report',
            'report_name': report_name,
            'report_type': 'qweb-pdf',
            'domain': [],
            'context': self.env.context,
            'data': {'label_qty': label_qty_map},
            'display_name': 'Custom Product Label',
        }
