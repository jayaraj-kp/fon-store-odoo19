from odoo import models, fields, api, _


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    partner_ref = fields.Char(string="Vendor Reference")

    # Confirmation Date (date_approve)
    date_approve_date = fields.Date(
        string="Confirmation Date",
        compute="_compute_date_approve_date",
        inverse="_inverse_date_approve_date",
        store=True,
    )
    # Expected Arrival (date_planned)
    date_planned_date = fields.Date(
        string="Expected Arrival",
        compute="_compute_date_planned_date",
        inverse="_inverse_date_planned_date",
        store=True,
    )
    # Order Deadline (date_order)
    date_order_date = fields.Date(
        string="Order Deadline",
        compute="_compute_date_order_date",
        inverse="_inverse_date_order_date",
        store=True,
    )

    @api.depends("date_approve")
    def _compute_date_approve_date(self):
        for rec in self:
            rec.date_approve_date = rec.date_approve.date() if rec.date_approve else False

    def _inverse_date_approve_date(self):
        for rec in self:
            if rec.date_approve_date:
                rec.date_approve = fields.Datetime.to_datetime(str(rec.date_approve_date))

    @api.depends("date_planned")
    def _compute_date_planned_date(self):
        for rec in self:
            rec.date_planned_date = rec.date_planned.date() if rec.date_planned else False

    def _inverse_date_planned_date(self):
        for rec in self:
            if rec.date_planned_date:
                rec.date_planned = fields.Datetime.to_datetime(str(rec.date_planned_date))

    @api.depends("date_order")
    def _compute_date_order_date(self):
        for rec in self:
            rec.date_order_date = rec.date_order.date() if rec.date_order else False

    def _inverse_date_order_date(self):
        for rec in self:
            if rec.date_order_date:
                rec.date_order = fields.Datetime.to_datetime(str(rec.date_order_date))


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    date_planned_date = fields.Date(
        string="Scheduled Date",
        compute="_compute_line_date_planned",
        store=True,
    )

    @api.depends("date_planned")
    def _compute_line_date_planned(self):
        for rec in self:
            rec.date_planned_date = rec.date_planned.date() if rec.date_planned else False
