# -*- coding: utf-8 -*-
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class ProductLabelLayout(models.TransientModel):
    """
    Inherit the standard product.label.layout wizard to add a
    'Show MRP Price' checkbox. When ticked, we inject show_mrp_price=True
    into the report data dict so the QWeb templates can render it.
    """
    _inherit = 'product.label.layout'

    show_mrp_price = fields.Boolean(
        string='Show MRP Price',
        default=False,
        help='When enabled, the MRP Price (mrp_price field) is printed on the label.',
    )

    def _prepare_report_data(self):
        """
        Call super() to get the standard xml_id and data dict,
        then inject our show_mrp_price flag into data.
        """
        xml_id, data = super()._prepare_report_data()
        data['show_mrp_price'] = self.show_mrp_price
        _logger.info(
            "MRP LABEL: xml_id=%s show_mrp_price=%s",
            xml_id, self.show_mrp_price,
        )
        return xml_id, data