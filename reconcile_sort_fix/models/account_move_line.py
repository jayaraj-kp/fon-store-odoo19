# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Override search to sort by amount match when called from reconcile widget.

        When context has 'reconcile_amount_sort', we fetch all results first,
        then sort so that lines whose abs(amount_residual) matches the target
        amount appear at the top.
        """
        target_amount = self.env.context.get("reconcile_amount_sort")
        if target_amount is None:
            return super().search(domain, offset=offset, limit=limit, order=order)

        # Fetch all matching records (ignore limit/offset for sorting purposes)
        all_records = super().search(domain, offset=0, limit=False, order=order)

        target = abs(float(target_amount))
        currency = self.env["res.currency"].browse(
            self.env.context.get("reconcile_currency_id")
        )
        precision = currency.decimal_places if currency else 2

        def sort_key(rec):
            residual = abs(rec.amount_residual)
            diff = abs(residual - target)
            # Exact match = 0, otherwise sort by closeness
            is_exact = round(diff, precision) == 0
            return (0 if is_exact else 1, diff)

        sorted_records = all_records.sorted(key=sort_key)

        # Apply offset and limit after sorting
        if offset:
            sorted_records = sorted_records[offset:]
        if limit:
            sorted_records = sorted_records[:limit]

        return sorted_records

    @api.model
    def search_count(self, domain, limit=None):
        """search_count does not need sorting, keep default behaviour."""
        return super().search_count(domain, limit=limit)
