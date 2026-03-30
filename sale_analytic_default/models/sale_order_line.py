# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """
        Override _get_view to forcefully remove the 'optional' attribute
        from analytic_distribution field in list views at runtime.
        This ensures the column is always visible regardless of user preferences
        or other view inheritances.
        """
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)

        if view_type == 'list':
            # Find all field nodes named analytic_distribution
            for node in arch.xpath("//field[@name='analytic_distribution']"):
                # Remove the optional attribute completely
                if 'optional' in node.attrib:
                    del node.attrib['optional']
                    _logger.debug(
                        "sale_analytic_default: Removed 'optional' attribute "
                        "from analytic_distribution in sale.order.line list view."
                    )
        return arch, view


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """
        Override _get_view on sale.order to also remove optional from
        analytic_distribution in the embedded order_line list inside the form.
        """
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)

        if view_type == 'form':
            for node in arch.xpath(
                "//field[@name='order_line']//field[@name='analytic_distribution']"
            ):
                if 'optional' in node.attrib:
                    del node.attrib['optional']
                    _logger.debug(
                        "sale_analytic_default: Removed 'optional' attribute "
                        "from analytic_distribution in sale.order form view."
                    )
        return arch, view
