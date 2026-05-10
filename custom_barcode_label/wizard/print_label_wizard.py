# # -*- coding: utf-8 -*-
# import json
# import logging
#
# from odoo import models, fields
#
# _logger = logging.getLogger(__name__)
#
#
# class PrintLabelWizard(models.TransientModel):
#     _name = 'custom_barcode_label.print_wizard'
#     _description = 'Print Barcode Labels Wizard'
#
#     label_qty = fields.Integer(
#         string='Copies per Label',
#         default=1,
#         required=True,
#     )
#
#     def action_open_print_dialog(self):
#         active_ids = self.env.context.get('active_ids', [])
#         active_model = self.env.context.get('active_model', 'product.product')
#         qty = max(1, self.label_qty)
#
#         _logger.info("WIZARD: active_ids=%s model=%s qty=%s", active_ids, active_model, qty)
#
#         if active_model == 'product.template':
#             products = (
#                 self.env['product.template']
#                 .browse(active_ids)
#                 .mapped('product_variant_ids')
#             )
#         else:
#             products = self.env['product.product'].browse(active_ids)
#
#         _logger.info("WIZARD: products=%s ids=%s", products.mapped('name'), products.ids)
#
#         if not products:
#             return {'type': 'ir.actions.act_window_close'}
#
#         # Save qty to config_parameter BEFORE the dialog opens the iframe
#         label_qty_map = {str(p.id): qty for p in products}
#         self.env['ir.config_parameter'].sudo().set_param(
#             'custom_barcode_label.pending_qty',
#             json.dumps(label_qty_map)
#         )
#         _logger.info("WIZARD: saved config_param=%s", label_qty_map)
#
#         # Build our custom controller URL for the iframe
#         ids_str = ','.join(str(i) for i in products.ids)
#         pdf_url = f'/custom_barcode_label/report/pdf/{ids_str}?qty={qty}'
#
#         names = products.mapped('name')
#         record_name = ', '.join(names[:2])
#         if len(names) > 2:
#             record_name += f' (+{len(names) - 2} more)'
#
#         _logger.info("WIZARD: pdf_url=%s", pdf_url)
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'custom_barcode_label.open_print_dialog',
#             'params': {
#                 'pdf_url': pdf_url,
#                 'record_name': record_name,
#                 'doc_label': 'Barcode Label',
#                 'label_qty': qty,
#                 'product_count': len(products),
#             },
#         }
# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class PrintLabelWizard(models.TransientModel):
    _name = 'custom_barcode_label.print_wizard'
    _description = 'Print Barcode Labels Wizard'

    label_qty = fields.Integer(
        string='Copies per Label',
        default=1,
        required=True,
    )

    show_mrp_price = fields.Boolean(
        string='Show MRP Price',
        default=False,
        help='When enabled, prints the MRP Price (mrp_price) on the label. '
             'When disabled, the Sales Price (lst_price) is shown.',
    )

    def action_open_print_dialog(self):
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.product')
        qty = max(1, self.label_qty)
        show_mrp = self.show_mrp_price

        _logger.info(
            "WIZARD: active_ids=%s model=%s qty=%s show_mrp=%s",
            active_ids, active_model, qty, show_mrp,
        )

        if active_model == 'product.template':
            products = (
                self.env['product.template']
                .browse(active_ids)
                .mapped('product_variant_ids')
            )
        else:
            products = self.env['product.product'].browse(active_ids)

        _logger.info("WIZARD: products=%s ids=%s", products.mapped('name'), products.ids)

        if not products:
            return {'type': 'ir.actions.act_window_close'}

        # Save qty + show_mrp to config_parameter BEFORE the dialog opens the iframe
        label_qty_map = {str(p.id): qty for p in products}
        self.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_qty',
            json.dumps(label_qty_map)
        )
        self.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_show_mrp',
            '1' if show_mrp else '0'
        )
        _logger.info(
            "WIZARD: saved config_param qty=%s show_mrp=%s",
            label_qty_map, show_mrp,
        )

        # Build our custom controller URL for the iframe
        ids_str = ','.join(str(i) for i in products.ids)
        pdf_url = (
            f'/custom_barcode_label/report/pdf/{ids_str}'
            f'?qty={qty}&show_mrp={1 if show_mrp else 0}'
        )

        names = products.mapped('name')
        record_name = ', '.join(names[:2])
        if len(names) > 2:
            record_name += f' (+{len(names) - 2} more)'

        _logger.info("WIZARD: pdf_url=%s", pdf_url)

        return {
            'type': 'ir.actions.client',
            'tag': 'custom_barcode_label.open_print_dialog',
            'params': {
                'pdf_url': pdf_url,
                'record_name': record_name,
                'doc_label': 'Barcode Label',
                'label_qty': qty,
                'product_count': len(products),
                'show_mrp_price': show_mrp,
            },
        }