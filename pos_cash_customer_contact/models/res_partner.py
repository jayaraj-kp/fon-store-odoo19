import traceback
import logging
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

CASH_CUSTOMER_NAME = "CASH CUSTOMER"


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ── Flag to mark contacts that belong only to CASH CUSTOMER ──────────────
    is_cash_customer_contact = fields.Boolean(
        string="Is Cash Customer Contact",
        default=False,
        index=True,
        help="If True, this contact is a sub-contact of CASH CUSTOMER and "
             "should not appear in the main Customers list.",
    )

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
        # Pre-mark any record being created under CASH CUSTOMER
        for vals in vals_list:
            parent_id = vals.get("parent_id")
            if parent_id:
                parent = self.browse(parent_id)
                if (
                    parent.exists()
                    and parent.name == CASH_CUSTOMER_NAME
                    and parent.is_company
                ):
                    vals["customer_rank"] = 0
                    vals["is_cash_customer_contact"] = True
                    _logger.info(
                        "PCB_DEBUG create() pre-marking as cash_customer_contact: %s",
                        vals.get("name"),
                    )

        records = super().create(vals_list)

        # Post-create: enforce again (in case ORM overrode our vals)
        cash_children = records.filtered(lambda r: r._is_cash_customer_child())
        if cash_children:
            _logger.info(
                "PCB_DEBUG create() post-enforce on: %s",
                cash_children.mapped("name"),
            )
            # Use SQL directly to bypass ALL ORM hooks and computed field triggers
            self.env.cr.execute(
                "UPDATE res_partner SET customer_rank = 0, is_cash_customer_contact = TRUE "
                "WHERE id = ANY(%s)",
                (cash_children.ids,),
            )
            cash_children.invalidate_recordset(["customer_rank", "is_cash_customer_contact"])
            for r in cash_children:
                _logger.info(
                    "PCB_DEBUG   VERIFIED => id=%s name=%s customer_rank=%s flag=%s",
                    r.id, r.name, r.customer_rank, r.is_cash_customer_contact,
                )

        return records

    def write(self, vals):
        res = super().write(vals)

        # After any write, enforce on cash customer children
        if "customer_rank" in vals and vals.get("customer_rank", 0) > 0:
            cash_children = self.filtered(lambda r: r._is_cash_customer_child())
            if cash_children:
                _logger.info(
                    "PCB_DEBUG write() enforcing customer_rank=0 via SQL for: %s",
                    cash_children.mapped("name"),
                )
                self.env.cr.execute(
                    "UPDATE res_partner SET customer_rank = 0, is_cash_customer_contact = TRUE "
                    "WHERE id = ANY(%s)",
                    (cash_children.ids,),
                )
                cash_children.invalidate_recordset(["customer_rank", "is_cash_customer_contact"])

        return res

    @api.model
    def _get_default_customers_domain(self):
        """Override to exclude CASH CUSTOMER sub-contacts from customers list."""
        domain = super()._get_default_customers_domain() if hasattr(super(), '_get_default_customers_domain') else [('customer_rank', '>', 0)]
        return domain + [('is_cash_customer_contact', '=', False)]