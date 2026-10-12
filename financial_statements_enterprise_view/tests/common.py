# Copyright 2024 YourCompany
# License: LGPL-3.0 or later

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


def _pick(company_data, *candidate_keys):
    """Return the first present, truthy key from ``company_data``.

    ``AccountTestInvoicingCommon.company_data`` fixture key names have
    shifted slightly between Odoo versions (e.g. 'default_account_revenue'
    vs 'default_account_income'). Trying a list of candidates keeps these
    tests from breaking on a minor version bump.
    """
    for key in candidate_keys:
        value = company_data.get(key)
        if value:
            return value
    raise KeyError(
        "None of %s found in company_data fixture — check the "
        "AccountTestInvoicingCommon fixture keys for your Odoo version."
        % (candidate_keys,)
    )


@tagged("post_install", "-at_install")
class FSEnterpriseCommon(AccountTestInvoicingCommon):
    """Base class for financial_statements_enterprise_view tests.

    Reuses Odoo core's AccountTestInvoicingCommon, which installs a real
    minimal chart of accounts and gives us `self.company_data` with
    ready-to-use accounts/journals for `self.company_data['company']` —
    exactly the same fixture Odoo's own accounting tests use, so the
    report engine sees a realistic chart_template-based setup rather than
    hand-rolled fake accounts.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.engine = cls.env["financial.report.engine"]

        cls.account_asset = _pick(
            cls.company_data, "default_account_assets", "default_account_asset"
        )
        cls.account_payable = _pick(cls.company_data, "default_account_payable")
        cls.account_receivable = _pick(cls.company_data, "default_account_receivable")
        cls.account_revenue = _pick(
            cls.company_data, "default_account_revenue", "default_account_income"
        )
        cls.account_expense = _pick(cls.company_data, "default_account_expense")
        cls.journal_misc = _pick(cls.company_data, "default_journal_misc")

    def _post_entry(self, date, account_amounts, journal=None):
        """Create and post a balanced account.move.

        :param date: ISO date string, e.g. "2024-06-15".
        :param account_amounts: list of (account_record, debit, credit) tuples.
        :param journal: journal to post through, defaults to Miscellaneous.
        """
        journal = journal or self.journal_misc
        move = self.env["account.move"].create({
            "move_type": "entry",
            "date": date,
            "journal_id": journal.id,
            "line_ids": [
                (0, 0, {
                    "account_id": account.id,
                    "debit": debit,
                    "credit": credit,
                    "name": "test line",
                })
                for account, debit, credit in account_amounts
            ],
        })
        move.action_post()
        return move

    @staticmethod
    def find_line(lines, line_id):
        """Depth-first search for a line dict by its 'id' key anywhere in
        a hierarchical report tree (as returned by get_balance_sheet /
        get_profit_and_loss)."""
        for line in lines:
            if line.get("id") == line_id:
                return line
            found = FSEnterpriseCommon.find_line(line.get("children") or [], line_id)
            if found:
                return found
        return None