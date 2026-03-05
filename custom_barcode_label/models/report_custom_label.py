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

        # Try 1: data dict passed directly from wizard
        label_qty = {}
        try:
            if data and isinstance(data.get('label_qty'), dict):
                label_qty = {int(k): int(v) for k, v in data['label_qty'].items()}
        except Exception:
            label_qty = {}

        # Try 2: fallback to ir.config_parameter set by wizard
        if not label_qty:
            try:
                import json
                raw = self.env['ir.config_parameter'].sudo().get_param(
                    'custom_barcode_label.pending_qty', '{}'
                )
                stored = json.loads(raw)
                label_qty = {int(k): int(v) for k, v in stored.items()
                             if int(k) in docids}
            except Exception:
                label_qty = {}

        # Try 3: hard default — 1 copy per product
        if not label_qty:
            label_qty = {doc.id: 1 for doc in docs}

        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _get_barcode(self, barcode_value):
        """Generate a Code128 barcode PNG as base64 data URI."""
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

            bc = Code128Barcode(str(barcode_value), barHeight=9*mm, barWidth=0.8)
            d = Drawing(70*mm, 10*mm)
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

        label_qty = {}
        try:
            if data and isinstance(data.get('label_qty'), dict):
                label_qty = {int(k): int(v) for k, v in data['label_qty'].items()}
        except Exception:
            label_qty = {}

        if not label_qty:
            try:
                import json
                raw = self.env['ir.config_parameter'].sudo().get_param(
                    'custom_barcode_label.pending_qty', '{}'
                )
                stored = json.loads(raw)
                product_ids = products.ids
                label_qty = {int(k): int(v) for k, v in stored.items()
                             if int(k) in product_ids}
            except Exception:
                label_qty = {}

        if not label_qty:
            label_qty = {p.id: 1 for p in products}

        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }
