# # -*- coding: utf-8 -*-
# from odoo import models, fields
#
#
# class ProductLabelWizardExtend(models.TransientModel):
#     """Extend the built-in Product Label Wizard to rename 'Show MRP' → 'Show Sales Price'."""
#     _inherit = 'product.label.wizard'
#
#     # Override the field just to change its string/label.
#     # The field already exists on the parent model; we only change the display name.
#     show_mrp = fields.Boolean(string='Show Sales Price')

# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductLabelWizardExtend(models.TransientModel):
    """
    Extend the built-in Product Label Wizard to:
    1. Rename 'Show MRP' → 'Show Sales Price' (field string override)
    2. Redirect 'Print Labels' to our custom report that shows mrp_price + lst_price
    """
    _inherit = 'product.label.wizard'

    # Override field string only — behaviour unchanged
    show_mrp = fields.Boolean(string='Show Sales Price')

    def action_print_labels(self):
        """
        Override the built-in action to redirect to our custom
        barcode label report which shows mrp_price + sales price.
        """
        # Collect product.product ids from the wizard selections
        # The wizard holds product_tmpl_ids and product_ids (variants)
        products = self.product_ids
        if not products:
            # Fall back to all variants of selected templates
            products = self.product_tmpl_ids.mapped('product_variant_ids')

        if not products:
            return {'type': 'ir.actions.act_window_close'}

        qty = max(1, self.quantity)

        _logger.info(
            "LABEL WIZARD OVERRIDE: products=%s qty=%s",
            products.ids, qty
        )

        # Save qty map to config_parameter (same mechanism as custom wizard)
        label_qty_map = {str(p.id): qty for p in products}
        self.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_qty',
            json.dumps(label_qty_map)
        )

        # Open our custom print-preview dialog
        ids_str = ','.join(str(i) for i in products.ids)
        pdf_url = f'/custom_barcode_label/report/pdf/{ids_str}?qty={qty}'

        names = products.mapped('name')
        record_name = ', '.join(names[:2])
        if len(names) > 2:
            record_name += f' (+{len(names) - 2} more)'

        return {
            'type': 'ir.actions.client',
            'tag': 'custom_barcode_label.open_print_dialog',
            'params': {
                'pdf_url': pdf_url,
                'record_name': record_name,
                'doc_label': 'Barcode Label',
                'label_qty': qty,
                'product_count': len(products),
            },
        }