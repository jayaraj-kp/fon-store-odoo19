# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PosCharityAccount(models.Model):
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
    # Accounting fields
    account_id = fields.Many2one(
        'account.account',
        string='Charity GL Account',
        help='The account where charity donations will be posted (e.g. Charity Payable or Charity Income).',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Charity Journal',
        help='Journal used to post charity donation entries. Leave empty to use the POS journal.',
    )

    @api.depends('donation_ids.amount', 'donation_ids.state')
    def _compute_total_donated(self):
        for rec in self:
            rec.total_donated = sum(
                rec.donation_ids.filtered(lambda d: d.state == 'confirmed').mapped('amount')
            )


class PosCharityDonation(models.Model):
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
    pos_session_id = fields.Many2one('pos.session', string='POS Session', ondelete='set null')
    pos_order_id = fields.Many2one('pos.order', string='POS Order', ondelete='set null')
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
    date = fields.Datetime(string='Donation Date', default=fields.Datetime.now)
    cashier_id = fields.Many2one('res.users', string='Cashier', default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status')
    note = fields.Char(string='Note')
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

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
        for rec in self:
            rec.write({'state': 'confirmed'})
            rec._create_journal_entry()

    def action_cancel(self):
        for rec in self:
            if rec.move_id:
                rec.move_id.button_cancel()
            rec.write({'state': 'cancelled'})

    def _create_journal_entry(self):
        """
        Create accounting journal entry for the charity donation.
        
        Debit:  Cash/Bank account (from POS payment method)
        Credit: Charity GL Account (configured on charity account)
        """
        self.ensure_one()
        
        # Check if accounting is available
        if not self.env['ir.module.module'].sudo().search([
            ('name', '=', 'account'), ('state', '=', 'installed')
        ]):
            _logger.info('Accounting module not installed, skipping journal entry')
            return

        charity = self.charity_account_id
        if not charity.account_id:
            _logger.warning('No GL account configured for charity %s, skipping journal entry', charity.name)
            return

        # Get the cash account from POS session's payment method
        cash_account = None
        if self.pos_session_id:
            cash_pm = self.pos_session_id.config_id.payment_method_ids.filtered(
                lambda pm: pm.is_cash_count
            )[:1]
            if cash_pm and cash_pm.receivable_account_id:
                cash_account = cash_pm.receivable_account_id
            elif cash_pm and hasattr(cash_pm, 'journal_id') and cash_pm.journal_id.default_account_id:
                cash_account = cash_pm.journal_id.default_account_id

        if not cash_account:
            # Fallback: use company's default cash account
            cash_account = self.env['account.account'].search([
                ('account_type', '=', 'asset_cash'),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

        if not cash_account:
            _logger.warning('Could not find cash account for charity journal entry')
            return

        # Determine journal
        journal = charity.journal_id
        if not journal and self.pos_session_id:
            # Use POS session's journal
            journal = self.pos_session_id.config_id.payment_method_ids.filtered(
                lambda pm: pm.is_cash_count
            )[:1].journal_id
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', 'in', ['cash', 'bank']),
                ('company_id', '=', self.env.company.id),
            ], limit=1)

        if not journal:
            _logger.warning('Could not find journal for charity journal entry')
            return

        move_vals = {
            'journal_id': journal.id,
            'date': self.date or fields.Date.today(),
            'ref': f'Charity Donation - {self.name} - {self.pos_order_id.name or ""}',
            'line_ids': [
                # Debit: Cash (money stays in drawer, we're just accounting for it)
                (0, 0, {
                    'account_id': cash_account.id,
                    'name': f'Charity donation - {self.charity_account_id.name}',
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                # Credit: Charity account
                (0, 0, {
                    'account_id': charity.account_id.id,
                    'name': f'Charity donation - {self.name}',
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ],
        }

        try:
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            self.move_id = move.id
            _logger.info('Journal entry %s created for charity donation %s', move.name, self.name)
        except Exception as e:
            _logger.error('Failed to create journal entry for charity donation %s: %s', self.name, str(e))
