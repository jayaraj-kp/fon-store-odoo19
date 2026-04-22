from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    partner_ref = fields.Char(required=True)

    date_approve_date = fields.Date(
        string="Confirmation Date",
        compute="_compute_date_approve_date",
        store=True,
    )
    date_planned_date = fields.Date(
        string="Expected Arrival",
        compute="_compute_date_planned_date",
        store=True,
    )

    @api.depends("date_approve")
    def _compute_date_approve_date(self):
        for rec in self:
            rec.date_approve_date = rec.date_approve.date() if rec.date_approve else False

    @api.depends("date_planned")
    def _compute_date_planned_date(self):
        for rec in self:
            rec.date_planned_date = rec.date_planned.date() if rec.date_planned else False
