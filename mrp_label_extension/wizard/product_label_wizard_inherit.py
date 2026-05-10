# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductLabelWizard(models.TransientModel):
    _inherit = 'product.label.wizard'

    show_mrp_price = fields.Boolean(
        string='Show MRP Price',
        default=False,
        help='When enabled, the MRP Price (mrp_price) is printed on the label.',
    )

    def action_print_labels(self):
        """
        Override the standard print action so we can inject show_mrp_price
        into the report data dict, which the QWeb template will read.
        """
        self.ensure_one()

        # Collect product variants the same way the standard wizard does
        products = self.product_ids
        if not products and self.product_tmpl_ids:
            products = self.product_tmpl_ids.mapped('product_variant_ids')

        if not products:
            return

        quantity = self.quantity
        label_type = self.label_type  # e.g. 'dymo', '2x7xprice', etc.

        # Build data dict — same keys the standard report expects, plus our flag
        data = {
            'quantity': quantity,
            'label_type': label_type,
            'show_mrp': self.show_mrp_price,
        }

        # Use the same report action the standard wizard uses
        report_action = self.env.ref('product_label_print.action_report_product_label')
        return report_action.with_context(
            active_ids=products.ids,
            active_model='product.product',
        ).report_action(products, data=data)