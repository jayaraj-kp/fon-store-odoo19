# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BarcodeLabelController(http.Controller):

    @http.route(
        '/custom_barcode_label/report/pdf/<path:rec_ids>',
        type='http', auth='user', methods=['GET'], csrf=False
    )
    def barcode_label_pdf(self, rec_ids, qty=1, show_mrp=0, **kwargs):
        """
        Serve barcode label PDF for the iframe preview.
        URL: /custom_barcode_label/report/pdf/<ids>?qty=<n>&show_mrp=<0|1>

        This is called by the print dialog iframe.
        Saves qty and show_mrp to config_parameter, then renders the report PDF.
        """
        try:
            qty = max(1, int(qty))
        except (ValueError, TypeError):
            qty = 1

        try:
            show_mrp = bool(int(show_mrp))
        except (ValueError, TypeError):
            show_mrp = False

        try:
            ids = [int(i) for i in rec_ids.split(',') if i.strip().isdigit()]
        except Exception:
            return request.make_response('Invalid IDs', status=400)

        if not ids:
            return request.make_response('No product IDs provided', status=400)

        _logger.info("BARCODE CTRL: ids=%s qty=%s show_mrp=%s", ids, qty, show_mrp)

        # Save to config_parameter — report _get_report_values reads this as fallback
        label_qty_map = {str(i): qty for i in ids}
        request.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_qty',
            json.dumps(label_qty_map)
        )
        request.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label.pending_show_mrp',
            '1' if show_mrp else '0'
        )
        _logger.info(
            "BARCODE CTRL: saved config_param qty=%s show_mrp=%s",
            label_qty_map, show_mrp,
        )

        # Render the report PDF — pass everything in data dict (primary path)
        report_name = 'custom_barcode_label.report_custom_label_document'
        report_sudo = request.env['ir.actions.report'].sudo()

        try:
            pdf_content, _mime = report_sudo._render_qweb_pdf(
                report_name,
                res_ids=ids,
                data={
                    'label_qty': label_qty_map,
                    'show_mrp_price': show_mrp,
                },
            )
        except Exception as e:
            _logger.error("BARCODE CTRL: render failed: %s", e)
            return request.make_response(
                f'PDF generation failed: {e}', status=500,
                headers=[('Content-Type', 'text/plain')]
            )

        _logger.info("BARCODE CTRL: PDF generated, size=%d bytes", len(pdf_content))

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'inline; filename="barcode_labels.pdf"'),
                ('Content-Length', str(len(pdf_content))),
                ('Cache-Control', 'no-store'),
            ]
        )


# # -*- coding: utf-8 -*-
# import json
# import logging
#
# from odoo import http
# from odoo.http import request
#
# _logger = logging.getLogger(__name__)
#
#
# class BarcodeLabelController(http.Controller):
#
#     @http.route(
#         '/custom_barcode_label/report/pdf/<path:rec_ids>',
#         type='http', auth='user', methods=['GET'], csrf=False
#     )
#     def barcode_label_pdf(self, rec_ids, qty=1, **kwargs):
#         """
#         Serve barcode label PDF for the iframe preview.
#         URL: /custom_barcode_label/report/pdf/<ids>?qty=<n>
#
#         This is called by the print dialog iframe.
#         Saves qty to config_parameter, then renders the report PDF.
#         """
#         try:
#             qty = max(1, int(qty))
#         except (ValueError, TypeError):
#             qty = 1
#
#         try:
#             ids = [int(i) for i in rec_ids.split(',') if i.strip().isdigit()]
#         except Exception:
#             return request.make_response('Invalid IDs', status=400)
#
#         if not ids:
#             return request.make_response('No product IDs provided', status=400)
#
#         _logger.info("BARCODE CTRL: ids=%s qty=%s", ids, qty)
#
#         # Save to config_parameter — report _get_report_values reads this
#         label_qty_map = {str(i): qty for i in ids}
#         request.env['ir.config_parameter'].sudo().set_param(
#             'custom_barcode_label.pending_qty',
#             json.dumps(label_qty_map)
#         )
#         _logger.info("BARCODE CTRL: saved config_param=%s", label_qty_map)
#
#         # Render the report PDF
#         report_name = 'custom_barcode_label.report_custom_label_document'
#         report_sudo = request.env['ir.actions.report'].sudo()
#
#         try:
#             pdf_content, _mime = report_sudo._render_qweb_pdf(
#                 report_name,
#                 res_ids=ids,
#                 data={'label_qty': label_qty_map},
#             )
#         except Exception as e:
#             _logger.error("BARCODE CTRL: render failed: %s", e)
#             return request.make_response(
#                 f'PDF generation failed: {e}', status=500,
#                 headers=[('Content-Type', 'text/plain')]
#             )
#
#         _logger.info("BARCODE CTRL: PDF generated, size=%d bytes", len(pdf_content))
#
#         return request.make_response(
#             pdf_content,
#             headers=[
#                 ('Content-Type', 'application/pdf'),
#                 ('Content-Disposition', 'inline; filename="barcode_labels.pdf"'),
#                 ('Content-Length', str(len(pdf_content))),
#                 ('Cache-Control', 'no-store'),
#             ]
#         )
