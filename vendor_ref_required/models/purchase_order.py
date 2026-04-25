from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    partner_ref = fields.Char(required=True)


class AccountMove(models.Model):
    _inherit ="account.move"

    ref = fields.Char(required = True)

