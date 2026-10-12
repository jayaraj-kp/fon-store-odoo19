from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Command
from odoo.tools import create_index


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # Helper used only by the GL/TB report filters. It is derived data
    # (mirror of analytic_distribution), so it is read-only for users: a manual
    # edit could make the report disagree with the journal item's real
    # analytic distribution. The ORM compute below still maintains it.
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_analytic_account_ids",
        store=True,
        readonly=True,
    )

    @api.model
    def _auto_init(self):
        """Create database indexes for General Ledger performance."""
        # Composite index for GL/TB queries: account_id, date, parent_state
        create_index(
            self._cr,
            "account_move_line_account_date_state_idx",
            "account_move_line",
            ["account_id", "date", "parent_state"],
        )
        # Index for initial balance queries: account_id, date, company_id
        create_index(
            self._cr,
            "account_move_line_account_date_company_idx",
            "account_move_line",
            ["account_id", "date", "company_id"],
        )
        # Note: analytic_account_ids is a Many2many (stored computed),
        # its relation table is indexed automatically by Odoo.
        return super()._auto_init()

    @api.depends("analytic_distribution")
    def _compute_analytic_account_ids(self):
        all_candidate_ids = set()
        rec_to_raw_ids = {}
        for rec in self:
            dist = rec.analytic_distribution
            if not dist:
                rec_to_raw_ids[rec.id] = []
                continue
            ids = set()
            for key in dist.keys():
                for part in key.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    try:
                        ids.add(int(part))
                    except (ValueError, TypeError):
                        continue
            rec_to_raw_ids[rec.id] = ids
            all_candidate_ids.update(ids)

        existing_ids = set()
        if all_candidate_ids:
            existing_ids = set(
                self.env["account.analytic.account"]
                .browse(list(all_candidate_ids))
                .exists()
                .ids
            )

        grouped = defaultdict(list)
        for rec in self:
            raw = rec_to_raw_ids.get(rec.id, set())
            valid = sorted(i for i in raw if i in existing_ids)
            grouped[tuple(valid)].append(rec.id)

        for ids_tuple, rec_ids in grouped.items():
            records = self.browse(rec_ids)
            records.analytic_account_ids = [Command.set(list(ids_tuple))]