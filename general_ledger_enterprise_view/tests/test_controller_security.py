# License: LGPL-3.0 or later
import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestGLEnterpriseControllerSecurity(HttpCase):
    """Verify _check_account_group and cross-company guards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_own = cls.env["res.company"].create({"name": "GL Test Own Co"})
        cls.company_other = cls.env["res.company"].create({"name": "GL Test Other Co"})
        cls.accountant = cls.env["res.users"].create({
            "name": "GL Test Accountant",
            "login": "gl_test_accountant",
            "password": "gl_test_accountant",
            "company_id": cls.company_own.id,
            "company_ids": [(6, 0, [cls.company_own.id])],
            "groups_id": [(6, 0, [cls.env.ref("account.group_account_user").id])],
        })
        cls.sales_user = cls.env["res.users"].create({
            "name": "GL Test Sales",
            "login": "gl_test_sales",
            "password": "gl_test_sales",
            "company_id": cls.company_own.id,
            "company_ids": [(6, 0, [cls.company_own.id])],
            "groups_id": [(6, 0, [cls.env.ref("sales_team.group_sale_salesman").id])],
        })

    def _json_rpc(self, url, params):
        payload = {"jsonrpc": "2.0", "method": "call", "params": params, "id": 1}
        return self.url_open(url, data=json.dumps(payload), headers={"Content-Type": "application/json"})

    def test_cross_company_denied_on_get_data(self):
        self.authenticate("gl_test_accountant", "gl_test_accountant")
        resp = self._json_rpc("/gl_enterprise/get_data", {
            "date_from": "2024-01-01", "date_to": "2024-12-31",
            "company_id": self.company_other.id,
        })
        body = resp.json()
        self.assertIn("error", body)

    def test_cross_company_denied_on_init(self):
        self.authenticate("gl_test_accountant", "gl_test_accountant")
        resp = self._json_rpc("/gl_enterprise/init", {"company_id": self.company_other.id})
        body = resp.json()
        self.assertIn("error", body)

    def test_non_accountant_denied(self):
        self.authenticate("gl_test_sales", "gl_test_sales")
        resp = self._json_rpc("/gl_enterprise/get_data", {
            "date_from": "2024-01-01", "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = resp.json()
        self.assertIn("error", body)

    def test_own_company_allowed(self):
        self.authenticate("gl_test_accountant", "gl_test_accountant")
        resp = self._json_rpc("/gl_enterprise/get_data", {
            "date_from": "2024-01-01", "date_to": "2024-12-31",
            "company_id": self.company_own.id,
        })
        body = resp.json()
        # Should succeed (may be empty accounts but no error)
        self.assertNotIn("error", body)

    def test_parent_state_domain_used(self):
        """The shared domain builder must filter on the stored parent_state
        (no join on move_id.state) and use the analytic helper field.

        Behaviour-based replacement for the old test that read main.py as
        text through a relative path (broke when cwd changed).
        """
        from odoo.addons.general_ledger_enterprise_view.controllers import main as gl_main

        company = self.company_own

        posted = gl_main._build_gl_base_domain(company, "posted")
        self.assertIn(("parent_state", "=", "posted"), posted)
        self.assertIn(("parent_state", "!=", "cancel"), posted)

        draft = gl_main._build_gl_base_domain(company, "draft")
        self.assertIn(("parent_state", "=", "draft"), draft)

        # 'all' keeps cancelled moves out but adds no positive state filter
        everything = gl_main._build_gl_base_domain(company, "all")
        self.assertIn(("parent_state", "!=", "cancel"), everything)
        self.assertNotIn(("parent_state", "=", "posted"), everything)
        self.assertNotIn(("parent_state", "=", "draft"), everything)

        # No join through move_id (the old, slower move_id.state domain)
        for leaf in posted:
            if isinstance(leaf, (tuple, list)):
                self.assertFalse(
                    str(leaf[0]).startswith("move_id."),
                    "domain must not join through move_id: %r" % (leaf,),
                )

        # Analytic filtering goes through the stored helper field
        self.assertEqual(
            gl_main._build_analytic_domain([1, 2]),
            [("analytic_account_ids", "in", [1, 2])],
        )
        self.assertEqual(gl_main._build_analytic_domain([]), [])
        self.assertIn(
            ("analytic_account_ids", "in", [7]),
            gl_main._build_gl_base_domain(company, "posted", analytic_ids=[7]),
        )

        # Cap against huge IN clauses
        capped = gl_main._build_analytic_domain(list(range(1, 500)))
        self.assertEqual(len(capped[0][2]), gl_main._MAX_ANALYTIC_IDS)