# # Copyright 2024 Custom Development
# # License: LGPL-3.0 or later
#
# import base64
# import logging
#
# from odoo import api, models
# from odoo.tools import file_open
#
# _logger = logging.getLogger(__name__)
#
#
# class ReportPartnerLedger(models.AbstractModel):
#     # IMPORTANT: _name must be "report.{report_name}" where report_name is
#     # the value in the ir.actions.report record's <report_name> field.
#     # report_name = "partner_ledger_enterprise_view.report_partner_ledger_pdf"
#     _name = "report.partner_ledger_enterprise_view.report_partner_ledger_pdf"
#     _description = "Partner Ledger PDF Report"
#     # _table override is required: the auto-generated table name exceeds
#     # PostgreSQL's 63-character limit (AbstractModels don't create real tables
#     # but Odoo still validates the length).
#     _table = "oca_pl_report_partner_ledger_pdf"
#
#     def _get_header_image_b64(self):
#         """Return a base64 data URI for the company header image.
#
#         Uses odoo.tools.file_open which correctly resolves module-relative
#         paths on any server deployment. wkhtmltopdf cannot load images via
#         HTTP, so we embed the image as a data URI.
#         """
#         try:
#             with file_open(
#                 "partner_ledger_enterprise_view/static/src/img/header.png",
#                 "rb",
#             ) as f:
#                 b64 = base64.b64encode(f.read()).decode("utf-8")
#             return "data:image/png;base64," + b64
#         except Exception as e:
#             _logger.error(
#                 "OCA Partner Ledger: failed to load header image: %s", e
#             )
#             return ""
#
#     @api.model
#     def _get_report_values(self, docids, data=None):
#         data = data or {}
#         return {
#             "doc_ids": docids,
#             "doc_model": "partner.ledger.engine",
#             "lines": data.get("lines", []),
#             "report_view": data.get("report_view", "partner_ledger"),
#             "report_title": data.get("report_title", "Partner Ledger"),
#             "company_name": data.get("company_name", ""),
#             "currency_symbol": data.get("currency_symbol", ""),
#             "date_from": data.get("date_from", ""),
#             "date_to": data.get("date_to", ""),
#             "header_image_b64": self._get_header_image_b64(),
#         }
# Copyright 2024 Custom Development
# License: LGPL-3.0 or later

import base64
import logging

from odoo import api, models
from odoo.tools import file_open

_logger = logging.getLogger(__name__)


class ReportPartnerLedger(models.AbstractModel):
    # IMPORTANT: _name must be "report.{report_name}" where report_name is
    # the value in the ir.actions.report record's <report_name> field.
    # report_name = "partner_ledger_enterprise_view.report_partner_ledger_pdf"
    _name = "report.partner_ledger_enterprise_view.report_partner_ledger_pdf"
    _description = "Partner Ledger PDF Report"
    # _table override is required: the auto-generated table name exceeds
    # PostgreSQL's 63-character limit (AbstractModels don't create real tables
    # but Odoo still validates the length).
    _table = "pl_report_partner_ledger_pdf"

    def _get_header_image_b64(self):
        """Return a base64 data URI for the company header image.

        Uses odoo.tools.file_open which correctly resolves module-relative
        paths on any server deployment. wkhtmltopdf cannot load images via
        HTTP, so we embed the image as a data URI.
        """
        try:
            with file_open(
                "partner_ledger_enterprise_view/static/src/img/header.png",
                "rb",
            ) as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            return "data:image/png;base64," + b64
        except Exception as e:
            _logger.error(
                "Partner Ledger: failed to load header image: %s", e
            )
            return ""

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        return {
            "doc_ids": docids,
            "doc_model": "partner.ledger.engine",
            "lines": data.get("lines", []),
            "report_view": data.get("report_view", "partner_ledger"),
            "report_title": data.get("report_title", "Partner Ledger"),
            "company_name": data.get("company_name", ""),
            "currency_symbol": data.get("currency_symbol", ""),
            "date_from": data.get("date_from", ""),
            "date_to": data.get("date_to", ""),
            "header_image_b64": self._get_header_image_b64(),
        }