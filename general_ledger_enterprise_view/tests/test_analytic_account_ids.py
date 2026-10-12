# License: LGPL-3.0 or later
"""Tests for the analytic_account_ids helper field and the pre_init_hook SQL
back-fill. The back-fill must give exactly the same links as the ORM compute."""
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.general_ledger_enterprise_view import hooks


@tagged("post_install", "-at_install")
class TestAnalyticAccountIds(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        plan_a = cls.env["account.analytic.plan"].create({"name": "GL Test Plan A"})
        plan_b = cls.env["account.analytic.plan"].create({"name": "GL Test Plan B"})
        Analytic = cls.env["account.analytic.account"]
        cls.a1 = Analytic.create({"name": "GL A1", "plan_id": plan_a.id})
        cls.a2 = Analytic.create({"name": "GL A2", "plan_id": plan_b.id})
        cls.a3 = Analytic.create({"name": "GL A3", "plan_id": plan_b.id})

        account_1 = cls.env["account.account"].create({
            "code": "GLAN01", "name": "GL Analytic Test 1",
            "account_type": "asset_receivable",
            "company_ids": [(6, 0, [company.id])],
        })
        account_2 = cls.env["account.account"].create({
            "code": "GLAN02", "name": "GL Analytic Test 2",
            "account_type": "income",
            "company_ids": [(6, 0, [company.id])],
        })
        journal = cls.env["account.journal"].create({
            "name": "GL Analytic Test", "code": "GLAN",
            "type": "general", "company_id": company.id,
        })
        a1, a2, a3 = cls.a1.id, cls.a2.id, cls.a3.id
        distributions = [
            {str(a1): 100},                       # single key
            {"%s,%s" % (a1, a2): 100},            # compound key (two plans)
            {str(a2): 50, str(a3): 50},           # two keys
            False,                                # no distribution
        ]
        cls.move = cls.env["account.move"].create({
            "date": "2024-01-15",
            "journal_id": journal.id,
            "move_type": "entry",
            "line_ids": [
                (0, 0, {
                    "account_id": (account_1 if i % 2 == 0 else account_2).id,
                    "debit": 10.0 if i % 2 == 0 else 0.0,
                    "credit": 0.0 if i % 2 == 0 else 10.0,
                    "analytic_distribution": dist or False,
                })
                for i, dist in enumerate(distributions)
            ],
        })
        cls.env.flush_all()

    # ------------------------------------------------------------------
    def _read_pairs(self, table, line_ids):
        self.env.cr.execute(
            'SELECT account_move_line_id, account_analytic_account_id FROM "%s" '
            "WHERE account_move_line_id IN %%s" % table,
            [tuple(line_ids)],
        )
        return set(self.env.cr.fetchall())

    # ------------------------------------------------------------------
    def test_helper_field_is_readonly_but_stored_computed(self):
        field = self.env["account.move.line"]._fields["analytic_account_ids"]
        self.assertTrue(field.readonly, "helper field must not be user-editable")
        self.assertTrue(field.store)
        self.assertTrue(field.compute)

    def test_orm_compute_links(self):
        """Sanity check of the existing compute, used as the reference below."""
        lines = self.move.line_ids.sorted("id")
        self.assertEqual(lines[0].analytic_account_ids, self.a1)
        self.assertEqual(lines[1].analytic_account_ids, self.a1 | self.a2)
        self.assertEqual(lines[2].analytic_account_ids, self.a2 | self.a3)
        self.assertFalse(lines[3].analytic_account_ids)

    def test_sql_backfill_matches_orm_compute(self):
        lines = self.move.line_ids
        expected = {(l.id, a.id) for l in lines for a in l.analytic_account_ids}
        self.assertTrue(expected)

        cr = self.env.cr
        # default batch size
        hooks._create_relation_table(cr, table="gl_test_rel_one")
        hooks._fill_relation(cr, table="gl_test_rel_one")
        self.assertEqual(self._read_pairs("gl_test_rel_one", lines.ids), expected)

        # several small id-range batches must give the identical result
        cr.execute("SELECT MIN(id), MAX(id) FROM account_move_line")
        lo, hi = cr.fetchone()
        small = max((hi - lo) // 3, 1)
        hooks._create_relation_table(cr, table="gl_test_rel_batched")
        hooks._fill_relation(cr, table="gl_test_rel_batched", batch_size=small)
        self.assertEqual(self._read_pairs("gl_test_rel_batched", lines.ids), expected)

    def test_sql_backfill_is_idempotent(self):
        cr = self.env.cr
        lines = self.move.line_ids
        hooks._create_relation_table(cr, table="gl_test_rel_idem")
        hooks._fill_relation(cr, table="gl_test_rel_idem")
        first = self._read_pairs("gl_test_rel_idem", lines.ids)
        hooks._fill_relation(cr, table="gl_test_rel_idem")   # second run: no error
        self.assertEqual(self._read_pairs("gl_test_rel_idem", lines.ids), first)

    def test_pre_init_hook_is_noop_when_table_exists(self):
        cr = self.env.cr
        cr.execute('SELECT COUNT(*) FROM "%s"' % hooks.REL_TABLE)
        before = cr.fetchone()[0]
        hooks.pre_init_hook(self.env)
        cr.execute('SELECT COUNT(*) FROM "%s"' % hooks.REL_TABLE)
        self.assertEqual(cr.fetchone()[0], before)

    def test_relation_names_match_the_registry(self):
        """Guards the hard-coded names against Odoo naming changes."""
        field = self.env["account.move.line"]._fields["analytic_account_ids"]
        self.assertEqual(field.relation, hooks.REL_TABLE)
        self.assertEqual(field.column1, hooks.COL_LINE)
        self.assertEqual(field.column2, hooks.COL_ANALYTIC)