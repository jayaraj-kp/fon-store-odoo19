# from odoo import api, models
# from odoo.osv import expression
#
#
# class PartnerLedgerEngine(models.AbstractModel):
#     """Builds Enterprise-style Partner Ledger data, grouped by partner
#     with expandable journal items and a running balance."""
#
#     _name = "partner.ledger.engine"
#     _description = "Partner Ledger Report Engine"
#
#     # ------------------------------------------------------------------
#     # Account type filtering (Trade Partners / Non Trade / Receivable / Payable)
#     # ------------------------------------------------------------------
#     def _account_type_domain(self, account_types):
#         """account_types: list among 'receivable', 'non_trade_receivable',
#         'payable', 'non_trade_payable'."""
#         if not account_types:
#             account_types = ["receivable", "payable"]
#
#         has_non_trade = "non_trade" in self.env["account.account"]._fields
#         sub_domains = []
#         for t in account_types:
#             if t == "receivable":
#                 d = [("account_type", "=", "asset_receivable")]
#                 if has_non_trade:
#                     d.append(("non_trade", "=", False))
#             elif t == "non_trade_receivable":
#                 if not has_non_trade:
#                     continue
#                 d = [
#                     ("account_type", "=", "asset_receivable"),
#                     ("non_trade", "=", True),
#                 ]
#             elif t == "payable":
#                 d = [("account_type", "=", "liability_payable")]
#                 if has_non_trade:
#                     d.append(("non_trade", "=", False))
#             elif t == "non_trade_payable":
#                 if not has_non_trade:
#                     continue
#                 d = [
#                     ("account_type", "=", "liability_payable"),
#                     ("non_trade", "=", True),
#                 ]
#             else:
#                 continue
#             sub_domains.append(d)
#
#         if not sub_domains:
#             return [("id", "=", 0)]
#         return expression.OR(sub_domains)
#
#     # ------------------------------------------------------------------
#     # Main entry point
#     # ------------------------------------------------------------------
#     @api.model
#     def get_partner_ledger(
#             self,
#             date_from,
#             date_to,
#             company_id=None,
#             account_types=None,
#             partner_ids=None,
#             tag_ids=None,
#             target_move="posted",
#     ):
#         company = (
#             self.env["res.company"].browse(company_id)
#             if company_id
#             else self.env.company
#         )
#
#         account_domain = self._account_type_domain(account_types)
#         accounts = self.env["account.account"].search(account_domain)
#
#         domain = [
#             ("account_id", "in", accounts.ids),
#             ("date", ">=", date_from),
#             ("date", "<=", date_to),
#             ("company_id", "=", company.id),
#             ("partner_id", "!=", False),
#             ("display_type", "not in", ["line_section", "line_note"]),
#         ]
#         if target_move == "posted":
#             domain.append(("parent_state", "=", "posted"))
#         else:
#             domain.append(("parent_state", "in", ["posted", "draft"]))
#         if partner_ids:
#             domain.append(("partner_id", "in", partner_ids))
#         if tag_ids:
#             domain.append(("partner_id.category_id", "in", tag_ids))
#
#         move_lines = self.env["account.move.line"].search(
#             domain, order="partner_id, date, id"
#         )
#
#         has_matching = "matching_number" in move_lines._fields
#         has_client_order_ref = "client_order_ref" in self.env["account.move"]._fields
#
#         partners_data = {}
#         order = []
#         for line in move_lines:
#             partner = line.partner_id
#             if partner.id not in partners_data:
#                 partners_data[partner.id] = {
#                     "partner": partner,
#                     "lines": [],
#                     "running": 0.0,
#                 }
#                 order.append(partner.id)
#             data = partners_data[partner.id]
#             data["running"] += (line.debit or 0.0) - (line.credit or 0.0)
#             move = line.move_id
#             data["lines"].append(
#                 {
#                     "id": "ml_%s" % line.id,
#                     "name": move.name or line.name or "",
#                     "move_id": move.id,
#                     "line_type": "account",
#                     "style": "account",
#                     "journal": line.journal_id.code or "",
#                     "account": line.account_id.code or "",
#                     "invoice_date": (
#                         move.invoice_date.isoformat()
#                         if getattr(move, "invoice_date", False)
#                         else (line.date.isoformat() if line.date else "")
#                     ),
#                     "due_date": (
#                         line.date_maturity.isoformat()
#                         if line.date_maturity
#                         else ""
#                     ),
#                     "matching": (
#                         line.matching_number
#                         if has_matching and line.matching_number
#                         else ""
#                     ),
#                     # Customer Reference: the "PO/Reference #" field (custom
#                     # field client_order_ref on account.move), populated only
#                     # for customer invoices/credit notes/receipts.
#                     "ref_customer": (
#                         (move.client_order_ref or "")
#                         if has_client_order_ref
#                            and move.move_type in ("out_invoice", "out_refund", "out_receipt")
#                         else ""
#                     ),
#                     # Vendor Reference: the standard account.move "ref" field,
#                     # holding the vendor's own document number, populated only
#                     # for vendor bills/refunds/receipts.
#                     "ref_vendor": (
#                         (move.ref or "")
#                         if move.move_type in ("in_invoice", "in_refund", "in_receipt")
#                         else ""
#                     ),
#                     "debit": round(line.debit or 0.0, 2),
#                     "credit": round(line.credit or 0.0, 2),
#                     "balance": round(data["running"], 2),
#                     "children": [],
#                 }
#             )
#
#         # Sort partners alphabetically by name (partners with no name last)
#         order.sort(key=lambda pid: (partners_data[pid]["partner"].name or "").lower())
#
#         total_debit = 0.0
#         total_credit = 0.0
#         total_balance = 0.0
#         partner_rows = []
#         for pid in order:
#             data = partners_data[pid]
#             partner = data["partner"]
#             p_debit = sum(l["debit"] for l in data["lines"])
#             p_credit = sum(l["credit"] for l in data["lines"])
#             p_balance = round(data["running"], 2)
#             total_debit += p_debit
#             total_credit += p_credit
#             total_balance += p_balance
#             partner_rows.append(
#                 {
#                     "id": "partner_%s" % pid,
#                     "name": partner.name or "",
#                     "partner_id": pid,
#                     "line_type": "partner",
#                     "style": "group",
#                     "journal": "",
#                     "account": "",
#                     "invoice_date": "",
#                     "due_date": "",
#                     "matching": "",
#                     "ref_customer": "",
#                     "ref_vendor": "",
#                     "debit": round(p_debit, 2),
#                     "credit": round(p_credit, 2),
#                     "balance": p_balance,
#                     "children": data["lines"],
#                 }
#             )
#
#         total_row = {
#             "id": "partner_ledger_total",
#             "name": "Partner Ledger",
#             "line_type": "total",
#             "style": "header",
#             "journal": "",
#             "account": "",
#             "invoice_date": "",
#             "due_date": "",
#             "matching": "",
#             "ref_customer": "",
#             "ref_vendor": "",
#             "debit": round(total_debit, 2),
#             "credit": round(total_credit, 2),
#             "balance": round(total_balance, 2),
#             "children": [],
#         }
#
#         return {
#             "lines": [total_row] + partner_rows,
#             "company_name": company.name,
#             "currency_name": company.currency_id.name,
#             "currency_symbol": company.currency_id.symbol,
#         }
#
#     @api.model
#     def has_unposted_entries(self, date_from, date_to, company_id=None):
#         company = (
#             self.env["res.company"].browse(company_id)
#             if company_id
#             else self.env.company
#         )
#         domain = [
#             ("date", ">=", date_from),
#             ("date", "<=", date_to),
#             ("company_id", "=", company.id),
#             ("state", "=", "draft"),
#         ]
#         return bool(self.env["account.move"].search_count(domain))

from odoo import api, models
from odoo.osv import expression
from odoo.tools import html2plaintext


class PartnerLedgerEngine(models.AbstractModel):
    """Builds Enterprise-style Partner Ledger data, grouped by partner
    with expandable journal items and a running balance."""

    _name = "partner.ledger.engine"
    _description = "Partner Ledger Report Engine"

    # ------------------------------------------------------------------
    # Account type filtering (Trade Partners / Non Trade / Receivable / Payable)
    # ------------------------------------------------------------------
    def _account_type_domain(self, account_types):
        """account_types: list among 'receivable', 'non_trade_receivable',
        'payable', 'non_trade_payable'."""
        if not account_types:
            account_types = ["receivable", "payable"]

        has_non_trade = "non_trade" in self.env["account.account"]._fields
        sub_domains = []
        for t in account_types:
            if t == "receivable":
                d = [("account_type", "=", "asset_receivable")]
                if has_non_trade:
                    d.append(("non_trade", "=", False))
            elif t == "non_trade_receivable":
                if not has_non_trade:
                    continue
                d = [
                    ("account_type", "=", "asset_receivable"),
                    ("non_trade", "=", True),
                ]
            elif t == "payable":
                d = [("account_type", "=", "liability_payable")]
                if has_non_trade:
                    d.append(("non_trade", "=", False))
            elif t == "non_trade_payable":
                if not has_non_trade:
                    continue
                d = [
                    ("account_type", "=", "liability_payable"),
                    ("non_trade", "=", True),
                ]
            else:
                continue
            sub_domains.append(d)

        if not sub_domains:
            return [("id", "=", 0)]
        return expression.OR(sub_domains)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    @api.model
    def get_partner_ledger(
            self,
            date_from,
            date_to,
            company_id=None,
            account_types=None,
            partner_ids=None,
            tag_ids=None,
            target_move="posted",
    ):
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )

        account_domain = self._account_type_domain(account_types)
        accounts = self.env["account.account"].search(account_domain)

        domain = [
            ("account_id", "in", accounts.ids),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
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

        has_matching = "matching_number" in move_lines._fields
        has_client_order_ref = "client_order_ref" in self.env["account.move"]._fields
        has_payment_id = "payment_id" in self.env["account.move.line"]._fields
        has_move_origin_payment = "origin_payment_id" in self.env["account.move"]._fields

        # The Char field on account.payment used for the reference typed in
        # when registering a payment has been renamed across Odoo versions
        # (e.g. "memo" vs "ref") and may not exist at all on a stripped-down
        # CE install without the full Accounting app. Detect whichever one is
        # actually present so this never raises on data load; fall back to
        # the payment's own move name ("name") if neither is available.
        payment_ref_field = False
        if has_payment_id:
            payment_fields = self.env["account.payment"]._fields
            for fname in ("ref", "memo", "name"):
                if fname in payment_fields:
                    payment_ref_field = fname
                    break

        # Narration source: payments take the payment's narration field
        # (a custom field added by this module); invoices/bills use the
        # narration entered on the originating sale/purchase order.
        payment_narration_field = False
        if has_payment_id or has_move_origin_payment:
            payment_fields = self.env["account.payment"]._fields
            if "narration" in payment_fields:
                payment_narration_field = "narration"

        has_sale_link = "sale_line_ids" in move_lines._fields
        has_purchase_link = "purchase_order_id" in move_lines._fields
        has_purchase_line = "purchase_line_id" in move_lines._fields
        has_invoice_origin = "invoice_origin" in self.env["account.move"]._fields

        narration_cache = {}

        def _line_narration(line, move):
            """Return the narration text for an account.move.line, cached
            per move. Payments use the payment's narration field;
            invoices/bills use move.narration first, then fall back to
            linked order narration."""
            if move.id in narration_cache:
                return narration_cache[move.id]
            narration = ""
            move_type = move.move_type
            payment = False
            if has_payment_id and line.payment_id:
                payment = line.payment_id
            elif has_move_origin_payment and move.origin_payment_id:
                payment = move.origin_payment_id
            if payment:
                narration = getattr(payment, payment_narration_field, "") or ""
                if not narration and move_type == "entry":
                    narration = move.ref or ""
            elif move_type == "entry":
                if move.narration:
                    narration = (html2plaintext(move.narration) or "").strip()
                if not narration:
                    narration = move.ref or ""
            elif move_type in ("out_invoice", "out_refund", "out_receipt"):
                if move.narration:
                    narration = (html2plaintext(move.narration) or "").strip()
                if not narration:
                    order = False
                    if has_sale_link and line.sale_line_ids:
                        order = line.sale_line_ids.order_id[:1]
                    if not order and has_invoice_origin:
                        origin = (move.invoice_origin or "").strip()
                        if origin:
                            order = self.env["sale.order"].search(
                                [("name", "=", origin)], limit=1
                            )
                    narration = order.narration or "" if order else ""
            elif move_type in ("in_invoice", "in_refund", "in_receipt"):
                if move.narration:
                    narration = (html2plaintext(move.narration) or "").strip()
                if not narration:
                    order = False
                    if has_purchase_link and line.purchase_order_id:
                        order = line.purchase_order_id
                    elif has_purchase_line and line.purchase_line_id:
                        order = line.purchase_line_id.order_id
                    if not order and has_invoice_origin:
                        origin = (move.invoice_origin or "").strip()
                        if origin:
                            order = self.env["purchase.order"].search(
                                [("name", "=", origin)], limit=1
                            )
                    narration = order.narration or "" if order else ""
            narration_cache[move.id] = narration
            return narration

        partners_data = {}
        order = []
        for line in move_lines:
            partner = line.partner_id
            if partner.id not in partners_data:
                partners_data[partner.id] = {
                    "partner": partner,
                    "lines": [],
                    "running": 0.0,
                }
                order.append(partner.id)
            data = partners_data[partner.id]
            data["running"] += (line.debit or 0.0) - (line.credit or 0.0)
            move = line.move_id
            data["lines"].append(
                {
                    "id": "ml_%s" % line.id,
                    "name": move.name or line.name or "",
                    "move_id": move.id,
                    "line_type": "account",
                    "style": "account",
                    "journal": line.journal_id.code or "",
                    "account": line.account_id.code or "",
                    "account_type": line.account_id.account_type or "",
                    "invoice_date": (
                        move.invoice_date.isoformat()
                        if getattr(move, "invoice_date", False)
                        else (line.date.isoformat() if line.date else "")
                    ),
                    "due_date": (
                        line.date_maturity.isoformat()
                        if line.date_maturity
                        else ""
                    ),
                    "matching": (
                        line.matching_number
                        if has_matching and line.matching_number
                        else ""
                    ),
                    # Reference: a single coordinated column carrying whichever
                    # reference is relevant to the entry -
                    #   - Customer invoices/credit notes/receipts: the
                    #     "PO/Reference #" field (custom field client_order_ref
                    #     on account.move).
                    #   - Vendor bills/refunds/receipts: the standard
                    #     account.move "ref" field (the vendor's own document
                    #     number).
                    #   - Anything else (e.g. payments, misc entries): falls
                    #     back to the payment's own reference when the line
                    #     originates from a registered payment.
                    "reference": (
                        (
                            (move.client_order_ref or "")
                            if has_client_order_ref
                               and move.move_type in ("out_invoice", "out_refund", "out_receipt")
                            else ""
                        )
                        or (
                            (move.ref or "")
                            if move.move_type in ("in_invoice", "in_refund", "in_receipt")
                            else ""
                        )
                        or (
                            (getattr(line.payment_id, payment_ref_field, "") or "")
                            if payment_ref_field and line.payment_id
                            else ""
                        )
                    ),
                    "narration": _line_narration(line, move),
                    "debit": round(line.debit or 0.0, 2),
                    "credit": round(line.credit or 0.0, 2),
                    "balance": round(data["running"], 2),
                    "children": [],
                }
            )

        # Sort partners alphabetically by name (partners with no name last)
        order.sort(key=lambda pid: (partners_data[pid]["partner"].name or "").lower())

        total_debit = 0.0
        total_credit = 0.0
        total_balance = 0.0
        partner_rows = []
        for pid in order:
            data = partners_data[pid]
            partner = data["partner"]
            p_debit = sum(l["debit"] for l in data["lines"])
            p_credit = sum(l["credit"] for l in data["lines"])
            p_balance = round(data["running"], 2)
            total_debit += p_debit
            total_credit += p_credit
            total_balance += p_balance
            partner_rows.append(
                {
                    "id": "partner_%s" % pid,
                    "name": partner.name or "",
                    "partner_id": pid,
                    "line_type": "partner",
                    "style": "group",
                    "journal": "",
                    "account": "",
                    "invoice_date": "",
                    "due_date": "",
                    "matching": "",
                    "reference": "",
                    "narration": "",
                    "debit": round(p_debit, 2),
                    "credit": round(p_credit, 2),
                    "balance": p_balance,
                    "children": data["lines"],
                }
            )

        total_row = {
            "id": "partner_ledger_total",
            "name": "Partner Ledger",
            "line_type": "total",
            "style": "header",
            "journal": "",
            "account": "",
            "invoice_date": "",
            "due_date": "",
            "matching": "",
            "reference": "",
            "narration": "",
            "debit": round(total_debit, 2),
            "credit": round(total_credit, 2),
            "balance": round(total_balance, 2),
            "children": [],
        }

        return {
            "lines": [total_row] + partner_rows,
            "company_name": company.name,
            "currency_name": company.currency_id.name,
            "currency_symbol": company.currency_id.symbol,
        }

    @api.model
    def has_unposted_entries(self, date_from, date_to, company_id=None):
        company = (
            self.env["res.company"].browse(company_id)
            if company_id
            else self.env.company
        )
        domain = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("company_id", "=", company.id),
            ("state", "=", "draft"),
        ]
        return bool(self.env["account.move"].search_count(domain))