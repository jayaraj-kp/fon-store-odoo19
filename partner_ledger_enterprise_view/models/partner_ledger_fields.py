from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    narration = fields.Text(
        string="Narration",
        help="Free-text narration shown in the interactive Partner Ledger "
             "view (not printed on the PDF).",
    )


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    narration = fields.Text(
        string="Narration",
        help="Free-text narration shown in the interactive Partner Ledger "
             "view (not printed on the PDF).",
    )


class AccountPayment(models.Model):
    _inherit = "account.payment"

    narration = fields.Text(
        string="Narration",
        help="Free-text narration shown in the Partner Ledger narration column.",
    )


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    narration = fields.Text(
        string="Narration",
        help="Free-text narration shown in the Partner Ledger narration column.",
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals["narration"] = self.narration
        return vals
