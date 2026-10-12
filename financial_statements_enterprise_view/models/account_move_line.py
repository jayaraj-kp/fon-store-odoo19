from collections import defaultdict

from odoo import api, fields, models
from odoo.fields import Command


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_analytic_account_ids",
        store=True,
    )

    @api.depends("analytic_distribution")
    def _compute_analytic_account_ids(self):
        # FIX (correctness + perf): previously used Command.link only, never
        # removing old links -> stale analytic_account_ids when distribution
        # changed or was cleared. Now uses Command.set to replace the whole
        # set atomically. Also batches writes by identical final set to avoid
        # N separate writes on large imports.
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

        # Group records that share the same final valid set -> one write per group
        grouped = defaultdict(list)
        for rec in self:
            raw = rec_to_raw_ids.get(rec.id, set())
            valid = sorted(i for i in raw if i in existing_ids)
            grouped[tuple(valid)].append(rec.id)

        for ids_tuple, rec_ids in grouped.items():
            records = self.browse(rec_ids)
            records.analytic_account_ids = [Command.set(list(ids_tuple))]
