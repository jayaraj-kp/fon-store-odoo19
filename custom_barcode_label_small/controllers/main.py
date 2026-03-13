# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SmallBarcodeLabelController(http.Controller):

    @http.route(
        '/custom_barcode_label_small/report/pdf/<path:rec_ids>',
        type='http', auth='user', methods=['GET'], csrf=False
    )
    def small_barcode_label_pdf(self, rec_ids, qty=1, **kwargs):
        """
        Serve 27x12mm barcode label PDF for the iframe preview.
        URL: /custom_barcode_label_small/report/pdf/<ids>?qty=<n>
        """
        try:
            qty = max(1, int(qty))
        except (ValueError, TypeError):
            qty = 1

        try:
            ids = [int(i) for i in rec_ids.split(',') if i.strip().isdigit()]
        except Exception:
            return request.make_response('Invalid IDs', status=400)

        if not ids:
            return request.make_response('No product IDs provided', status=400)

        _logger.info("SMALL LABEL CTRL: ids=%s qty=%s", ids, qty)

        # Save qty to config_parameter — report _get_report_values reads this
        label_qty_map = {str(i): qty for i in ids}
        request.env['ir.config_parameter'].sudo().set_param(
            'custom_barcode_label_small.pending_qty',
            json.dumps(label_qty_map)
        )

        report_name = 'custom_barcode_label_small.report_small_label_main'

        try:
            pdf_content, _mime = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                report_name,
                res_ids=ids,
                data={'label_qty': label_qty_map},
            )
        except Exception as e:
            _logger.error("SMALL LABEL CTRL: render failed: %s", e)
            return request.make_response(
                f'PDF generation failed: {e}', status=500,
                headers=[('Content-Type', 'text/plain')]
            )

        _logger.info("SMALL LABEL CTRL: PDF generated, %d bytes", len(pdf_content))

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', 'inline; filename="small_barcode_labels.pdf"'),
                ('Content-Length', str(len(pdf_content))),
                ('Cache-Control', 'no-store'),
            ]
        )
