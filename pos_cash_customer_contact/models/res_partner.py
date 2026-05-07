from odoo import models, api

CASH_CUSTOMER_NAME = "CASH CUSTOMER"


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _is_cash_customer_child(self):
        """Return True if this partner is a direct child of CASH CUSTOMER company."""
        self.ensure_one()
        return (
            not self.is_company
            and self.parent_id
            and self.parent_id.name == CASH_CUSTOMER_NAME
            and self.parent_id.is_company
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # After creation, reset customer_rank to 0 for any child of CASH CUSTOMER
        cash_children = records.filtered(lambda r: r._is_cash_customer_child())
        if cash_children:
            cash_children.write({"customer_rank": 0})
        return records

    def write(self, vals):
        res = super().write(vals)
        # If customer_rank is being set (e.g. by POS order processing), block it
        if "customer_rank" in vals and vals.get("customer_rank", 0) > 0:
            cash_children = self.filtered(lambda r: r._is_cash_customer_child())
            if cash_children:
                # Use sudo + direct SQL-level bypass via super to avoid infinite loop
                super(ResPartner, cash_children).write({"customer_rank": 0})
        return res