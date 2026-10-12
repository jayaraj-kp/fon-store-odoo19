# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestFSEnterpriseControllerSecurity(HttpCase):
    """Exercises main.py over real JSON-RPC HTTP calls (not just Python
    method calls) so we actually prove the AccessError checks fire the
    way a browser client would hit them.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_own = cls.env["res.company"].create({"name": "FS Test Own Co"})
        cls.company_other = cls.env["res.company"].create({"name": "FS Test Other Co"})
        cls.user = cls.env["res.users"].create({
            "name": "FS Test Accountant",
            "login": "fs_test_accountant",
            "password": "fs_test_accountant",
            "company_id": cls.company_own.id,
            "company_ids": [(6, 0, [cls.company_own.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    def test_cross_company_access_denied_on_get_data(self):
        """A user must not be able to fetch another company's report by
        simply passing its id in the RPC payload — this is the exact
        check documented in main.py's get_data()."""
        self.authenticate("fs_test_accountant", "fs_test_accountant")
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_other.id,
        })
        body = response.json()
        self.assertIn("error", body, "Expected a JSON-RPC error for cross-company access")
        self.assertIn("do not have access", json.dumps(body["error"]).lower())

    def test_cross_company_access_denied_on_init(self):
        """Same check in get_init_data()."""
        self.authenticate("fs_test_accountant", "fs_test_accountant")
        response = self._json_rpc("/fs_enterprise/init", {
            "company_id": self.company_other.id,
        })
        body = response.json()
        self.assertIn("error", body)

    def test_own_company_access_allowed(self):
        self.authenticate("fs_test_accountant", "fs_test_accountant")
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = response.json()
        self.assertNotIn("error", body)
        self.assertIn("lines", body.get("result", {}))

    def test_comparison_periods_capped_at_max(self):
        """More than _MAX_COMPARISON_PERIODS (12) periods must be
        silently truncated, not crash or fan out into dozens of report
        computations per request."""
        self.authenticate("fs_test_accountant", "fs_test_accountant")
        periods = [{"label": f"P{i}", "date_to": "2024-01-31"} for i in range(20)]
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
            "company_id": self.company_own.id,
            "comparison_mode": "previous_period",
            "comparison_periods": periods,
        })
        body = response.json()
        self.assertNotIn("error", body)
        cols = body["result"].get("comparison_columns", [])
        self.assertLessEqual(len(cols), 12)

    def test_analytic_accounts_filtered_by_company(self):
        """get_analytic_accounts must not leak another company's
        analytic accounts to a user browsing their own company."""
        analytic_own = self.env["account.analytic.account"].create(
            {"name": "Own Co Analytic XYZ", "company_id": self.company_own.id}
        )
        analytic_other = self.env["account.analytic.account"].create(
            {"name": "Other Co Analytic XYZ", "company_id": self.company_other.id}
        )
        self.authenticate("fs_test_accountant", "fs_test_accountant")
        response = self._json_rpc("/fs_enterprise/get_analytic_accounts", {
            "company_id": self.company_own.id,
        })
        body = response.json()
        names = [a["name"] for a in body.get("result", [])]
        self.assertIn(analytic_own.name, names)
        self.assertNotIn(analytic_other.name, names)

    def test_unauthenticated_request_rejected(self):
        """auth='user' routes must reject anonymous callers outright."""
        response = self._json_rpc("/fs_enterprise/get_data", {
            "report_type": "bs",
            "date_to": "2024-12-31",
        })
        body = response.json()
        self.assertIn("error", body)