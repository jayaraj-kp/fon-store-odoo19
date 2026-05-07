import traceback
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

CASH_CUSTOMER_NAME = "CASH CUSTOMER"


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _is_cash_customer_child(self):
        """Return True if this partner is a direct child of CASH CUSTOMER company."""
        self.ensure_one()
        result = (
            not self.is_company
            and self.parent_id
            and self.parent_id.name == CASH_CUSTOMER_NAME
            and self.parent_id.is_company
        )
        _logger.info(
            "PCB_DEBUG _is_cash_customer_child | partner=%s (id=%s) | "
            "is_company=%s | parent=%s | parent_is_company=%s | RESULT=%s",
            self.name, self.id,
            self.is_company,
            self.parent_id.name if self.parent_id else None,
            self.parent_id.is_company if self.parent_id else None,
            result,
        )
        return result

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info("PCB_DEBUG create() called with %d records", len(vals_list))
        for i, v in enumerate(vals_list):
            _logger.info("PCB_DEBUG   vals[%d] = %s", i, v)

        records = super().create(vals_list)

        for r in records:
            _logger.info(
                "PCB_DEBUG   AFTER super().create => id=%s name=%s "
                "customer_rank=%s parent_id=%s is_company=%s",
                r.id, r.name, r.customer_rank,
                r.parent_id.name if r.parent_id else None,
                r.is_company,
            )

        cash_children = records.filtered(lambda r: r._is_cash_customer_child())
        _logger.info("PCB_DEBUG   cash_children count = %d", len(cash_children))

        if cash_children:
            _logger.info(
                "PCB_DEBUG   Resetting customer_rank=0 for: %s",
                cash_children.mapped("name"),
            )
            cash_children.sudo().write({"customer_rank": 0})

            for r in cash_children:
                r.invalidate_recordset(["customer_rank"])
                _logger.info(
                    "PCB_DEBUG   AFTER reset write => id=%s name=%s customer_rank=%s",
                    r.id, r.name, r.customer_rank,
                )

        return records

    def write(self, vals):
        if "customer_rank" in vals:
            _logger.info(
                "PCB_DEBUG write() called on ids=%s names=%s | "
                "customer_rank being set to %s",
                self.ids,
                self.mapped("name"),
                vals.get("customer_rank"),
            )
            stack = "".join(traceback.format_stack())
            _logger.info("PCB_DEBUG write() CALL STACK:\n%s", stack)

        res = super().write(vals)

        if "customer_rank" in vals and vals.get("customer_rank", 0) > 0:
            cash_children = self.filtered(lambda r: r._is_cash_customer_child())
            if cash_children:
                _logger.info(
                    "PCB_DEBUG write() blocking customer_rank>0 for: %s",
                    cash_children.mapped("name"),
                )
                super(ResPartner, cash_children.sudo()).write({"customer_rank": 0})

                for r in cash_children:
                    r.invalidate_recordset(["customer_rank"])
                    _logger.info(
                        "PCB_DEBUG   AFTER block write => id=%s name=%s customer_rank=%s",
                        r.id, r.name, r.customer_rank,
                    )

        return res