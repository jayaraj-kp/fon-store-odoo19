# -*- coding: utf-8 -*-
import json
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class ReportSmallLabel(models.AbstractModel):
    _name = 'report.custom_barcode_label_small.report_small_label_main'
    _description = 'Custom Small Product Label Report (27x12mm)'
    _table = 'report_cbl_small_lbl_main'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("SMALL LABEL: docids=%s data=%s", docids, data)
        docs = self.env['product.product'].browse(docids)
        label_qty = self._resolve_qty(docids, data)
        return {
            'doc_ids':     docids,
            'doc_model':   'product.product',
            'docs':        docs,
            'label_qty':   label_qty,
        }

    @api.model
    def _resolve_qty(self, docids, data):
        # Layer 1: data dict
        try:
            if data and isinstance(data.get('label_qty'), dict):
                parsed = {int(k): int(v) for k, v in data['label_qty'].items()}
                if parsed:
                    return parsed
        except Exception as e:
            _logger.warning("SMALL LABEL: data dict error: %s", e)

        # Layer 2: ir.config_parameter
        try:
            raw = self.env['ir.config_parameter'].sudo().get_param(
                'custom_barcode_label_small.pending_qty', '{}'
            )
            stored = json.loads(raw or '{}')
            parsed = {int(k): int(v) for k, v in stored.items() if int(k) in docids}
            if parsed:
                self.env['ir.config_parameter'].sudo().set_param(
                    'custom_barcode_label_small.pending_qty', '{}'
                )
                return parsed
        except Exception as e:
            _logger.warning("SMALL LABEL: config_param error: %s", e)

        # Layer 3: default
        return {doc_id: 1 for doc_id in docids}


class ReportSmallLabelTmpl(models.AbstractModel):
    _name = 'report.custom_barcode_label_small.report_small_label_tmpl_main'
    _description = 'Custom Small Product Label Report (27x12mm) — template'
    _table = 'report_cbl_small_lbl_tmpl_main'
    _inherit = 'report.custom_barcode_label_small.report_small_label_main'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("SMALL LABEL TMPL: docids=%s data=%s", docids, data)
        docs = self.env['product.template'].browse(docids)
        products = docs.mapped('product_variant_ids')
        product_ids = products.ids
        label_qty = self._resolve_qty(product_ids, data)
        return {
            'doc_ids':     docids,
            'doc_model':   'product.template',
            'docs':        products,
            'label_qty':   label_qty,
        }



# # -*- coding: utf-8 -*-
# import base64
# import io
# import json
# import logging
#
# from odoo import models, api
#
# _logger = logging.getLogger(__name__)
#
#
# class ReportSmallLabel(models.AbstractModel):
#     # _name must match: "report." + report_name (with first dot replaced)
#     # report_name = custom_barcode_label_small.report_small_label_main
#     # → model _name = report.custom_barcode_label_small.report_small_label_main
#     _name = 'report.custom_barcode_label_small.report_small_label_main'
#     _description = 'Custom Small Product Label Report (27x12mm)'
#     _table = 'report_cbl_small_lbl_main'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         _logger.info("SMALL LABEL: docids=%s data=%s", docids, data)
#         docs = self.env['product.product'].browse(docids)
#         label_qty = self._resolve_qty(docids, data)
#         return {
#             'doc_ids':     docids,
#             'doc_model':   'product.product',
#             'docs':        docs,
#             'label_qty':   label_qty,
#             'get_barcode': self._get_barcode,
#         }
#
#     @api.model
#     def _resolve_qty(self, docids, data):
#         # Layer 1: data dict
#         try:
#             if data and isinstance(data.get('label_qty'), dict):
#                 parsed = {int(k): int(v) for k, v in data['label_qty'].items()}
#                 if parsed:
#                     return parsed
#         except Exception as e:
#             _logger.warning("SMALL LABEL: data dict error: %s", e)
#
#         # Layer 2: ir.config_parameter
#         try:
#             raw = self.env['ir.config_parameter'].sudo().get_param(
#                 'custom_barcode_label_small.pending_qty', '{}'
#             )
#             stored = json.loads(raw or '{}')
#             parsed = {int(k): int(v) for k, v in stored.items() if int(k) in docids}
#             if parsed:
#                 self.env['ir.config_parameter'].sudo().set_param(
#                     'custom_barcode_label_small.pending_qty', '{}'
#                 )
#                 return parsed
#         except Exception as e:
#             _logger.warning("SMALL LABEL: config_param error: %s", e)
#
#         # Layer 3: default
#         return {doc_id: 1 for doc_id in docids}
#
#     @api.model
#     def _get_barcode(self, barcode_value):
#         if not barcode_value:
#             return ''
#         try:
#             import barcode
#             from barcode.writer import ImageWriter
#             buf = io.BytesIO()
#             barcode.get('code128', str(barcode_value), writer=ImageWriter()).write(
#                 buf, options={
#                     'write_text': False, 'module_height': 10.0,
#                     'quiet_zone': 2.0, 'font_size': 0, 'text_distance': 0,
#                 })
#             buf.seek(0)
#             return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
#         except Exception as e:
#             _logger.warning("SMALL LABEL: python-barcode failed: %s", e)
#         try:
#             from reportlab.graphics.barcode.code128 import Code128Barcode
#             from reportlab.lib.units import mm
#             from reportlab.graphics.shapes import Drawing
#             from reportlab.graphics import renderPM
#             bc = Code128Barcode(str(barcode_value), barHeight=9 * mm, barWidth=0.8)
#             d = Drawing(70 * mm, 10 * mm)
#             d.add(bc)
#             buf = io.BytesIO()
#             renderPM.drawToFile(d, buf, fmt='PNG', dpi=96)
#             buf.seek(0)
#             return 'data:image/png;base64,' + base64.b64encode(buf.read()).decode()
#         except Exception as e:
#             _logger.warning("SMALL LABEL: reportlab failed: %s", e)
#         return ''
#
#
# class ReportSmallLabelTmpl(models.AbstractModel):
#     _name = 'report.custom_barcode_label_small.report_small_label_tmpl_main'
#     _description = 'Custom Small Product Label Report (27x12mm) — template'
#     _table = 'report_cbl_small_lbl_tmpl_main'
#     _inherit = 'report.custom_barcode_label_small.report_small_label_main'
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         _logger.info("SMALL LABEL TMPL: docids=%s data=%s", docids, data)
#         docs = self.env['product.template'].browse(docids)
#         products = docs.mapped('product_variant_ids')
#         product_ids = products.ids
#         label_qty = self._resolve_qty(product_ids, data)
#         return {
#             'doc_ids':     docids,
#             'doc_model':   'product.template',
#             'docs':        products,
#             'label_qty':   label_qty,
#             'get_barcode': self._get_barcode,
#         }
