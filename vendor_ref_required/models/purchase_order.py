from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    partner_ref = fields.Char(required=True)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        for move in self:
            if move.move_type == 'in_invoice' and not move.ref:
                raise UserError(_("Vendor Reference is required on Vendor Bills."))
        return super()._post(soft=soft)