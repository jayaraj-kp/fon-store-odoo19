# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PosCharityAccount(models.Model):
    """
    A simple charity account (ledger) that stores donations.
    This does NOT require the accounting module.
    """
    _name = 'pos.charity.account'
    _description = 'POS Charity Account'
    _rec_name = 'name'

    name = fields.Char(string='Charity Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
    total_donated = fields.Float(
        string='Total Donated',
        compute='_compute_total_donated',
        store=True,
    )
    donation_ids = fields.One2many(
        'pos.charity.donation', 'charity_account_id',
        string='Donations',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    @api.depends('donation_ids.amount', 'donation_ids.state')
    def _compute_total_donated(self):
        for rec in self:
            rec.total_donated = sum(
                rec.donation_ids.filtered(lambda d: d.state == 'confirmed').mapped('amount')
            )


class PosCharityDonation(models.Model):
    """
    Each time a customer donates at POS, a record is created here.
    """
    _name = 'pos.charity.donation'
    _description = 'POS Charity Donation'
    _order = 'date desc'

    name = fields.Char(string='Reference', readonly=True, default='New')
    charity_account_id = fields.Many2one(
        'pos.charity.account',
        string='Charity Account',
        required=True,
        ondelete='restrict',
    )
    pos_session_id = fields.Many2one(
        'pos.session',
        string='POS Session',
        ondelete='set null',
    )
    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        ondelete='set null',
    )
    pos_config_id = fields.Many2one(
        'pos.config',
        string='POS',
        related='pos_session_id.config_id',
        store=True,
    )
    amount = fields.Float(string='Donated Amount', required=True)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Datetime(
        string='Donation Date',
        default=fields.Datetime.now,
    )
    cashier_id = fields.Many2one(
        'res.users',
        string='Cashier',
        default=lambda self: self.env.user,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status')
    note = fields.Char(string='Note')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.charity.donation') or 'New'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError('Donation amount must be greater than zero.')

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
