from dateutil.relativedelta import relativedelta

from odoo import api, models
from odoo.osv import expression


class AgedReceivableEngine(models.AbstractModel):
    """Builds Aged Receivable data with aging buckets."""

    _name = "aged.receivable.engine"
    _description = "Aged Receivable Report Engine"

    @api.model
    def get_aged_receivable(
        self,
        date_as_of,
        company_id=None,
        account_types=None,
        partner_ids=None,
        tag_ids=None,
        target_move="posted",
        days_interval=30,
        based_on="due_date",
    ):
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )

        if not account_types:
            account_types = ["receivable"]

        sub_domains = []
        for t in account_types:
            if t == "receivable":
                sub_domains.append([("account_type", "=", "asset_receivable")])
            elif t == "payable":
                sub_domains.append([("account_type", "=", "liability_payable")])

        if not sub_domains:
            return {
                "lines": [],
                "company_name": company.name,
                "currency_name": company.currency_id.name,
                "currency_symbol": company.currency_id.symbol,
            }

        account_domain = expression.OR(sub_domains)
        accounts = self.env["account.account"].search(account_domain)

        domain = [
            ("account_id", "in", accounts.ids),
            ("date", "<=", date_as_of),
            ("company_id", "=", company.id),
            ("partner_id", "!=", False),
            ("display_type", "not in", ["line_section", "line_note"]),
        ]
        if target_move == "posted":
            domain.append(("parent_state", "=", "posted"))
        else:
            domain.append(("parent_state", "in", ["posted", "draft"]))
        if partner_ids:
            domain.append(("partner_id", "in", partner_ids))
        if tag_ids:
            domain.append(("partner_id.category_id", "in", tag_ids))

        move_lines = self.env["account.move.line"].search(
            domain, order="partner_id, date, id"
        )

        as_of_date = self._parse_date(date_as_of)

        partners_data = {}
        order = []
        for line in move_lines:
            partner = line.partner_id
            if partner.id not in partners_data:
                partners_data[partner.id] = {
                    "partner": partner,
                    "lines": [],
                    "buckets": {str(i): 0.0 for i in range(6)},
                }
                order.append(partner.id)

            data = partners_data[partner.id]

            balance = (line.debit or 0.0) - (line.credit or 0.0)
            if abs(balance) < 0.005:
                continue

            bucket = self._compute_bucket(
                line, as_of_date, days_interval, based_on
            )

            move = line.move_id
            invoice_date = ""
            if getattr(move, "invoice_date", False):
                invoice_date = move.invoice_date.isoformat()
            elif line.date:
                invoice_date = line.date.isoformat()

            due_date = ""
            if line.date_maturity:
                due_date = line.date_maturity.isoformat()
            elif line.date:
                due_date = line.date.isoformat()

            ref = ""
            if move.move_type in ("out_invoice", "out_refund", "out_receipt"):
                ref = getattr(move, "client_order_ref", "") or move.ref or ""
            elif move.move_type in ("in_invoice", "in_refund", "in_receipt"):
                ref = move.ref or ""
            else:
                ref = move.ref or ""

            data["lines"].append(
                {
                    "id": "ml_%s" % line.id,
                    "name": move.name or line.name or "",
                    "move_id": move.id,
                    "partner_id": partner.id,
                    "line_type": "account",
                    "invoice_date": invoice_date,
                    "due_date": due_date,
                    "reference": ref,
                    "debit": round(line.debit or 0.0, 2),
                    "credit": round(line.credit or 0.0, 2),
                    "balance": round(balance, 2),
                    "bucket": bucket,
                }
            )
            data["buckets"][bucket] += balance

        order.sort(key=lambda pid: (partners_data[pid]["partner"].name or "").lower())

        bucket_labels = self._bucket_labels(days_interval)

        total_buckets = {str(i): 0.0 for i in range(6)}
        total_balance = 0.0
        partner_rows = []
        for pid in order:
            data = partners_data[pid]
            partner = data["partner"]
            p_balance = sum(l["balance"] for l in data["lines"])
            if abs(p_balance) < 0.005:
                continue
            for k, v in data["buckets"].items():
                total_buckets[k] += v
            total_balance += p_balance
            partner_rows.append(
                {
                    "id": "partner_%s" % pid,
                    "name": partner.name or "",
                    "partner_id": pid,
                    "line_type": "partner",
                    "buckets": {k: round(v, 2) for k, v in data["buckets"].items()},
                    "total": round(p_balance, 2),
                    "children": data["lines"],
                }
            )

        total_row = {
            "id": "aged_receivable_total",
            "name": "Aged Receivable",
            "line_type": "total",
            "buckets": {k: round(v, 2) for k, v in total_buckets.items()},
            "total": round(total_balance, 2),
            "children": [],
        }

        return {
            "lines": [total_row] + partner_rows,
            "bucket_labels": bucket_labels,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
        }

    def _compute_bucket(self, line, as_of_date, days_interval, based_on="due_date"):
        if based_on == "invoice_date":
            ref_date = False
            move = line.move_id
            if getattr(move, "invoice_date", False):
                ref_date = move.invoice_date
            elif line.date:
                ref_date = line.date
        else:
            ref_date = line.date_maturity
            if not ref_date:
                ref_date = line.date

        if not ref_date:
            return "5"

        if isinstance(ref_date, str):
            from datetime import date as dt_date
            try:
                ref_date = dt_date.fromisoformat(ref_date)
            except Exception:
                return "5"

        diff = (as_of_date - ref_date).days

        if diff <= 0:
            return "0"

        num_buckets = max(1, 120 // days_interval) if days_interval else 4
        for i in range(1, num_buckets + 1):
            if diff <= i * days_interval:
                return str(i)

        return str(min(num_buckets + 1, 5))

    def _bucket_labels(self, days_interval=30):
        if days_interval == 30:
            return ["At Date", "1-30", "31-60", "61-90", "91-120", "Older"]
        elif days_interval == 15:
            return ["At Date", "1-15", "16-30", "31-45", "46-60", "Older"]
        elif days_interval == 60:
            return ["At Date", "1-60", "61-120", "121-180", "181-240", "Older"]
        else:
            labels = ["At Date"]
            for i in range(1, 5):
                start = (i - 1) * days_interval + 1
                end = i * days_interval
                labels.append("%s-%s" % (start, end))
            labels.append("Older")
            return labels

    def _parse_date(self, date_str):
        from datetime import date as dt_date
        if isinstance(date_str, dt_date):
            return date_str
        try:
            return dt_date.fromisoformat(date_str)
        except Exception:
            from datetime import date
            return date.today()

    def has_unposted_entries(self, date_as_of, company_id=None):
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )
        domain = [
            ("date", "<=", date_as_of),
            ("company_id", "=", company.id),
            ("state", "=", "draft"),
        ]
        return bool(self.env["account.move"].search_count(domain))
