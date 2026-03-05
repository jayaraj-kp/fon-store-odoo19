# -*- coding: utf-8 -*-
from odoo import models, fields


class PrintLabelWizard(models.TransientModel):
    _name = 'custom_barcode_label.print_wizard'
    _description = 'Print Barcode Labels Wizard'

    label_qty = fields.Integer(
        string='Copies per Label',
        default=1,
        required=True,
    )

    def action_download_pdf(self):
        """
        Store qty in config_parameter so the report model can read it
        reliably, then trigger the PDF report action.
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
            report_ref = 'custom_barcode_label.action_report_custom_label_tmpl'
        else:
            products = self.env['product.product'].browse(active_ids)
            report_ref = 'custom_barcode_label.action_report_custom_label'

        # Store qty per product_id in config param as JSON
        import json
        label_qty_map = {str(p.id): qty for p in products}
        self.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_qty',
            json.dumps(label_qty_map)
        )

        return self.env.ref(report_ref).report_action(
            products.ids,
            data={'label_qty': label_qty_map},
        )
