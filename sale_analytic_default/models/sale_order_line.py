# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('analytic_distribution')
    def _check_analytic_distribution_required(self):
        """
        Server-side constraint: analytic_distribution must be set
        on every sale order line. This fires on save regardless of
        how the record is created (UI, import, API, etc.).
        """
        for line in self:
            # Skip section and note lines (display_type set)
            if line.display_type:
                continue
            if not line.analytic_distribution:
                raise ValidationError(
                    _('Analytic Distribution is required on all order lines.\n'
                      'Please set it on product "%s".') % (line.product_id.display_name or _('Unknown'))
                )

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """
        Override _get_view to:
        1. Remove 'optional' attribute so column is always visible.
        2. Add required='1' so the UI shows the red asterisk.
        """
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)

        if view_type == 'list':
            for node in arch.xpath("//field[@name='analytic_distribution']"):
                if 'optional' in node.attrib:
                    del node.attrib['optional']
                node.set('required', '1')
        return arch, view


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """
        Override _get_view on sale.order to remove optional and
        mark analytic_distribution as required in the embedded list.
        """
        arch, view = super()._get_view(view_id=view_id, view_type=view_type, **options)

        if view_type == 'form':
            for node in arch.xpath(
                "//field[@name='order_line']//field[@name='analytic_distribution']"
            ):
                if 'optional' in node.attrib:
                    del node.attrib['optional']
                node.set('required', '1')
        return arch, view
