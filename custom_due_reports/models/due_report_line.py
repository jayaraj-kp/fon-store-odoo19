# -*- coding: utf-8 -*-
from odoo import models, fields


class DueReportLine(models.TransientModel):
    _name = 'due.report.line'
    _description = 'Due Report Line (on-screen View)'
    _order = 'sino asc'

    wizard_id = fields.Many2one('due.report.wizard', ondelete='cascade', required=True)
    move_type = fields.Selection(related='wizard_id.move_type', store=True)
    move_id = fields.Many2one('account.move', string='Document')

    sino = fields.Integer(string='SlNo')
    vno = fields.Char(string='VNo')
    inv_number = fields.Char(string='Inv.Number')
    date = fields.Date(string='Date')
    partner_id = fields.Many2one('res.partner', string='Party Name')
    due_day = fields.Integer(string='Due Day')
    due_date = fields.Date(string='Due Date')
    rem_over_days = fields.Integer(string='Days')
    rem_over_label = fields.Char(string='Status')
    narration = fields.Char(string='Narration')
    bill_amount = fields.Monetary(string='Bill Amount')
    paid = fields.Monetary(string='Paid')
    balance = fields.Monetary(string='Balance')
    total_amount = fields.Monetary(string='Total Amount')
    salesman_id = fields.Many2one('res.users', string='Salesman')
    lpo = fields.Char(string='L.P.O')

    currency_id = fields.Many2one('res.currency', string='Currency')
    company_id = fields.Many2one('res.company', string='Company')
