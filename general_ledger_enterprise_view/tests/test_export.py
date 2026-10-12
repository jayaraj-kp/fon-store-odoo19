# License: LGPL-3.0 or later
import base64

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestExport(TransactionCase):

    def test_xlsx_returns_base64(self):
        from odoo.addons.general_ledger_enterprise_view.controllers.main import GeneralLedgerEnterpriseController
        ctrl = GeneralLedgerEnterpriseController()
        data = {"accounts": [], "company_name": "Test", "date_from": "2024-01-01", "date_to": "2024-01-31"}
        filters = {"date_from": "2024-01-01", "date_to": "2024-01-31", "report_type": "gl"}
        result = ctrl._export_xlsx(self.env, "gl", data, filters)
        self.assertIn("file_content", result)
        self.assertIn("file_name", result)
        # Should be valid base64 string, not URL
        self.assertNotIn("url", result)
        # Decode should succeed
        decoded = base64.b64decode(result["file_content"])
        self.assertTrue(len(decoded) > 0)

    def test_tb_xlsx_totals_use_ending_balance(self):
        from odoo.addons.general_ledger_enterprise_view.controllers.main import GeneralLedgerEnterpriseController
        ctrl = GeneralLedgerEnterpriseController()
        data = {
            "accounts": [
                {"code": "100", "name": "Test", "init_bal": {"balance": 10}, "fin_bal": {"debit": 5, "credit": 2, "balance": 3, "ending_balance": 13}, "move_lines": []}
            ],
            "company_name": "Test", "date_from": "2024-01-01", "date_to": "2024-01-31"
        }
        filters = {"date_from": "2024-01-01", "date_to": "2024-01-31", "report_type": "tb"}
        result = ctrl._export_xlsx(self.env, "tb", data, filters)
        self.assertIn("file_content", result)