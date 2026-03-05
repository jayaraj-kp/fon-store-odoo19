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
        qty = int(data.get('qty', 1)) if data else 1
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'qty': qty,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _get_barcode(self, barcode_value):
        """Generate barcode image as base64 data URI."""
        try:
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
        except Exception:
            pass

        try:
            from reportlab.graphics.barcode.code128 import Code128Barcode
            from reportlab.lib.units import mm
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics import renderPM

            bc = Code128Barcode(str(barcode_value), barHeight=9 * mm, barWidth=0.8)
            d = Drawing(70 * mm, 10 * mm)
            d.add(bc)
            buf = io.BytesIO()
            renderPM.drawToFile(d, buf, fmt='PNG', dpi=96)
            buf.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
        except Exception:
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
        qty = int(data.get('qty', 1)) if data else 1
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'qty': qty,
            'get_barcode': self._get_barcode,
        }
