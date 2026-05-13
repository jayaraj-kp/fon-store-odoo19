# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.exceptions import UserError


CASH_CUSTOMER_NAME = "CASH CUSTOMER"


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def create_pos_cash_contact(self, vals):
        """Create exactly one contact under the CASH CUSTOMER company (POS).

        Single server entry point avoids duplicate ``res.partner`` rows from the
        POS UI (e.g. quick-create plus dialog, or double submit). Child contacts
        use ``customer_rank`` 0 so they are not treated as separate top-level
        customers.
        """
        self.check_access_rights("create")
        vals = dict(vals or {})
        name = (vals.get("name") or "").strip()
        if not name:
            raise UserError("Name is required.")

        parent = self.sudo().search(
            [("name", "=", CASH_CUSTOMER_NAME), ("is_company", "=", True)],
            limit=1,
        )
        if not parent:
            parent = self.sudo().create(
                {
                    "name": CASH_CUSTOMER_NAME,
                    "is_company": True,
                    "customer_rank": 1,
                }
            )

        tag_commands = vals.pop("category_id", False)

        partner_vals = {
            "name": name,
            "phone": vals.get("phone") or False,
            "mobile": vals.get("mobile") or False,
            "email": vals.get("email") or False,
            "parent_id": parent.id,
            "is_company": False,
            "type": "contact",
            "customer_rank": 0,
            "supplier_rank": 0,
        }
        if tag_commands:
            partner_vals["category_id"] = tag_commands

        partner = self.create(partner_vals)
        return partner.id