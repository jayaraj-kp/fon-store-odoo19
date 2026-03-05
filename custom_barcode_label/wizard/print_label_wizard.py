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

    def action_print(self):
        """Called from the wizard button — passes qty to the report."""
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')

        if active_model == 'product.template':
            products = self.env['product.template'].browse(active_ids).mapped(
                'product_variant_ids'
            )
            report_ref = 'custom_barcode_label.action_report_custom_label_tmpl'
        else:
            products = self.env['product.product'].browse(active_ids)
            report_ref = 'custom_barcode_label.action_report_custom_label'

        qty = max(1, self.label_qty)
        label_qty_map = {p.id: qty for p in products}

        return self.env.ref(report_ref).report_action(
            products.ids,
            data={'label_qty': {str(k): v for k, v in label_qty_map.items()}},
        )
