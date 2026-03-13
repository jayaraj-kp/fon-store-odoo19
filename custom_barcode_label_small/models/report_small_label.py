# -*- coding: utf-8 -*-
import base64
import io
import json
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ReportSmallLabel(models.AbstractModel):
    _name = 'report.custom_bc_small.report_small_label_document'
    _description = 'Custom Small Product Label Report (27x12mm) — product.product'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("SMALL LABEL: docids=%s data=%s", docids, data)
        docs = self.env['product.product'].browse(docids)
        label_qty = self._resolve_qty(docids, data)
        _logger.info("SMALL LABEL: label_qty=%s", label_qty)
        return {
            'doc_ids':    docids,
            'doc_model':  'product.product',
            'docs':       docs,
            'label_qty':  label_qty,
            'get_barcode': self._get_barcode,
        }

    @api.model
    def _resolve_qty(self, docids, data):
        """
        Resolve qty with 3 fallback layers:
        1. data dict passed from controller
        2. ir.config_parameter (set by wizard)
        3. default 1
        """
        # Layer 1: data dict
        try:
            if data and isinstance(data.get('label_qty'), dict):
                parsed = {int(k): int(v) for k, v in data['label_qty'].items()}
                if parsed:
                    _logger.info("SMALL LABEL: qty from data dict: %s", parsed)
                    return parsed
        except Exception as e:
            _logger.warning("SMALL LABEL: data dict error: %s", e)

        # Layer 2: ir.config_parameter
        try:
            raw = self.env['ir.config_parameter'].sudo().get_param(
                'custom_barcode_label_small.pending_qty', '{}'
            )
            _logger.info("SMALL LABEL: config_param raw=%s", raw)
            stored = json.loads(raw or '{}')
            parsed = {int(k): int(v) for k, v in stored.items() if int(k) in docids}
            if parsed:
                _logger.info("SMALL LABEL: qty from config_param: %s", parsed)
                self.env['ir.config_parameter'].sudo().set_param(
                    'custom_barcode_label_small.pending_qty', '{}'
                )
                return parsed
        except Exception as e:
            _logger.warning("SMALL LABEL: config_param error: %s", e)

        # Layer 3: default
        _logger.info("SMALL LABEL: using default qty=1")
        return {doc_id: 1 for doc_id in docids}

    @api.model
    def _get_barcode(self, barcode_value):
        if not barcode_value:
            return ''
        # Try python-barcode first
        try:
            import barcode
            from barcode.writer import ImageWriter
            buf = io.BytesIO()
            barcode.get('code128', str(barcode_value), writer=ImageWriter()).write(
                buf, options={
                    'write_text':  False,
                    'module_height': 10.0,
                    'quiet_zone':  2.0,
                    'font_size':   0,
                    'text_distance': 0,
                })
            buf.seek(0)
            return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
        except Exception as e:
            _logger.warning("SMALL LABEL: python-barcode failed: %s", e)

        # Fallback: reportlab
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
            _logger.warning("SMALL LABEL: reportlab failed: %s", e)

        return ''


class ReportSmallLabelTmpl(models.AbstractModel):
    _name = 'report.custom_bc_small.report_small_label_tmpl_document'
    _description = 'Custom Small Product Label Report (27x12mm) — product.template'
    _inherit = 'report.custom_bc_small.report_small_label_document'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("SMALL LABEL TMPL: docids=%s data=%s", docids, data)
        docs = self.env['product.template'].browse(docids)
        products = docs.mapped('product_variant_ids')
        product_ids = products.ids
        label_qty = self._resolve_qty(product_ids, data)
        _logger.info("SMALL LABEL TMPL: label_qty=%s", label_qty)
        return {
            'doc_ids':    docids,
            'doc_model':  'product.template',
            'docs':       products,
            'label_qty':  label_qty,
            'get_barcode': self._get_barcode,
        }
