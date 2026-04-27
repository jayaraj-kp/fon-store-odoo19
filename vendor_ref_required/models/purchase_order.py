from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    partner_ref = fields.Char(required=True)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.constrains('ref', 'move_type')
    def _check_vendor_bill_ref(self):
        for move in self:
            if move.move_type == 'in_invoice' and not move.ref:
                raise ValidationError("Vendor Reference is required on Vendor Bills.")