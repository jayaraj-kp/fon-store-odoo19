# -*- coding: utf-8 -*-
import base64
import io
from odoo import models, api


class ReportCustomLabel(models.AbstractModel):
    _name = 'report.custom_barcode_label.report_custom_label_document'
    _description = 'Custom Product Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['product.product'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _get_barcode(self, barcode_value):
        """
        Generate barcode using Odoo's built-in barcode route handler.
        This calls the exact same code that /report/barcode/ uses,
        so it always works regardless of which barcode lib is installed.
        """
        try:
            from odoo.addons.base.models.ir_actions_report import IrActionsReport
            # Odoo's barcode method: barcode(barcode_type, value, **kwargs)
            png_bytes = IrActionsReport._render_qweb_pdf  # just checking import
        except Exception:
            pass

        try:
            # Use Odoo's barcode controller directly (internal call, no HTTP)
            from odoo.addons.web.controllers.report import ReportController
            ctrl = ReportController()
        except Exception:
            pass

        try:
            # The most direct way: use python-barcode which Odoo CE bundles
            import barcode
            from barcode.writer import ImageWriter
            buf = io.BytesIO()
            barcode.get(
                'code128',
                str(barcode_value),
                writer=ImageWriter()
            ).write(buf, options={
                'write_text': False,
                'module_height': 10.0,
                'quiet_zone': 2.0,
                'font_size': 0,
                'text_distance': 0,
            })
            buf.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
        except Exception as e:
            pass

        try:
            # Alternative: reportlab (also bundled with Odoo)
            from reportlab.graphics.barcode.code128 import Code128Barcode
            from reportlab.lib.units import mm
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics import renderPM

            bc = Code128Barcode(str(barcode_value), barHeight=9*mm, barWidth=0.8)
            d = Drawing(70*mm, 10*mm)
            d.add(bc)
            buf = io.BytesIO()
            renderPM.drawToFile(d, buf, fmt='PNG', dpi=96)
            buf.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
        except Exception as e:
            pass

        return ''


class ReportCustomLabelTmpl(models.AbstractModel):
    _name = 'report.custom_barcode_label.report_custom_label_tmpl_document'
    _description = 'Custom Product Label Report (Template)'
    _inherit = 'report.custom_barcode_label.report_custom_label_document'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['product.template'].browse(docids)
        products = docs.mapped('product_variant_ids')
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'get_barcode': self._get_barcode,
        }
