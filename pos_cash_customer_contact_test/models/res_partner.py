from odoo import api, models

CASH_CUSTOMER_NAME = "CASH CUSTOMER"


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def get_cash_customer_parent_id(self):
        """Return the id of the 'CASH CUSTOMER' parent company.

        Used by the POS "Create" / "Create and edit..." options so that every
        new POS customer is created as a contact under this one parent.
        The parent is searched case-insensitively (CASH CUSTOMER / Cash Customer)
        and is created only if it does not exist yet.
        """
        Partner = self.sudo().with_context(active_test=False)
        parent = Partner.search([
            ("name", "=ilike", CASH_CUSTOMER_NAME),
            ("is_company", "=", True),
            ("parent_id", "=", False),
        ], limit=1)
        if not parent:
            parent = Partner.create({
                "name": CASH_CUSTOMER_NAME,
                "is_company": True,
                "customer_rank": 1,
            })
        elif not parent.active:
            parent.active = True
        return parent.id
