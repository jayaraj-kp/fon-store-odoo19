# -*- coding: utf-8 -*-
import base64
import io
import json
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ReportCustomLabel(models.AbstractModel):
    _name = 'report.custom_barcode_label.report_custom_label_document'
    _description = 'Custom Product Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("BARCODE LABEL: docids=%s data=%s", docids, data)
        docs = self.env['product.product'].browse(docids)
        label_qty = self._resolve_qty(docids, data)
        _logger.info("BARCODE LABEL: label_qty=%s", label_qty)
        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'docs': docs,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _resolve_qty(self, docids, data):
        """
        Resolve qty with 3 fallback layers.
        Keys are always converted to int to match product.id (int).
        """
        # Layer 1: data dict
        try:
            if data and isinstance(data.get('label_qty'), dict):
                parsed = {int(k): int(v) for k, v in data['label_qty'].items()}
                if parsed:
                    _logger.info("BARCODE: qty from data dict: %s", parsed)
                    return parsed
        except Exception as e:
            _logger.warning("BARCODE: data dict error: %s", e)

        # Layer 2: ir.config_parameter (set by wizard just before opening dialog)
        try:
            raw = self.env['ir.config_parameter'].sudo().get_param(
                'custom_barcode_label.pending_qty', '{}'
            )
            _logger.info("BARCODE: config_param raw=%s docids=%s", raw, docids)
            stored = json.loads(raw or '{}')
            parsed = {int(k): int(v) for k, v in stored.items() if int(k) in docids}
            if parsed:
                _logger.info("BARCODE: qty from config_param: %s", parsed)
                # Clear after use so stale data doesn't affect next print
                self.env['ir.config_parameter'].sudo().set_param(
                    'custom_barcode_label.pending_qty', '{}'
                )
                return parsed
            else:
                _logger.warning("BARCODE: config_param had no matching ids. stored=%s docids=%s", stored, docids)
        except Exception as e:
            _logger.warning("BARCODE: config_param error: %s", e)

        # Layer 3: default 1
        _logger.info("BARCODE: using default qty=1")
        return {doc_id: 1 for doc_id in docids}

    @api.model
    def _get_barcode(self, barcode_value):
        if not barcode_value:
            return ''
        try:
            import barcode
            from barcode.writer import ImageWriter
            buf = io.BytesIO()
            barcode.get('code128', str(barcode_value), writer=ImageWriter()).write(
                buf, options={
                    'write_text': False, 'module_height': 10.0,
                    'quiet_zone': 2.0, 'font_size': 0, 'text_distance': 0,
                })
            buf.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
        except Exception as e:
            _logger.warning("BARCODE: python-barcode failed: %s", e)
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
        except Exception as e:
            _logger.warning("BARCODE: reportlab failed: %s", e)
        return ''


class ReportCustomLabelTmpl(models.AbstractModel):
    _name = 'report.custom_barcode_label.report_custom_label_tmpl_document'
    _description = 'Custom Product Label Report (Template)'
    _inherit = 'report.custom_barcode_label.report_custom_label_document'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("BARCODE TMPL: docids=%s data=%s", docids, data)
        docs = self.env['product.template'].browse(docids)
        products = docs.mapped('product_variant_ids')
        product_ids = products.ids
        label_qty = self._resolve_qty(product_ids, data)
        _logger.info("BARCODE TMPL: label_qty=%s", label_qty)
        return {
            'doc_ids': docids,
            'doc_model': 'product.template',
            'docs': products,
            'label_qty': label_qty,
            'get_barcode': self._get_barcode,
        }
