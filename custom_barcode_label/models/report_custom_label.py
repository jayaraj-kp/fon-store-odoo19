# -*- coding: utf-8 -*-
import base64
import io
import json
from odoo import models, api


class ReportCustomLabel(models.AbstractModel):
    _name = 'report.custom_barcode_label.report_custom_label_document'
    _description = 'Custom Product Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['product.product'].browse(docids)
        label_qty = self._load_label_qty(docids, data)
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _load_label_qty(self, docids, data):
        """
        Load label qty with 3 fallback layers:
        1. data dict (may not work in Odoo 17+/19 but try anyway)
        2. ir.config_parameter — saved by wizard BEFORE calling report
        3. Default 1 copy per product
        """
        label_qty = {}

        # Layer 1 — data dict
        try:
            if data and isinstance(data.get('label_qty'), dict):
                parsed = {int(k): int(v) for k, v in data['label_qty'].items()}
                if parsed:
                    label_qty = parsed
        except Exception:
            pass

        # Layer 2 — config parameter set by wizard
        if not label_qty:
            try:
                raw = self.env['ir.config_parameter'].sudo().get_param(
                    'custom_barcode_label.pending_qty', '{}'
                )
                stored = json.loads(raw or '{}')
                parsed = {int(k): int(v) for k, v in stored.items()
                          if int(k) in docids}
                if parsed:
                    label_qty = parsed
                    # Clear after use
                    self.env['ir.config_parameter'].sudo().set_param(
                        'custom_barcode_label.pending_qty', '{}'
                    )
            except Exception:
                pass

        # Layer 3 — default 1
        if not label_qty:
            label_qty = {doc_id: 1 for doc_id in docids}

        return label_qty

    @api.model
    def _get_barcode(self, barcode_value):
        """Generate Code128 barcode as base64 PNG data URI."""
        if not barcode_value:
            return ''
        try:
            import barcode
            from barcode.writer import ImageWriter
            buf = io.BytesIO()
            barcode.get(
                'code128', str(barcode_value), writer=ImageWriter()
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
        product_ids = products.ids
        label_qty = self._load_label_qty(product_ids, data)
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }
