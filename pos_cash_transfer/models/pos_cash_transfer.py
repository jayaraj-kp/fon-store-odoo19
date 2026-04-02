from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosCashTransfer(models.Model):
    _name = 'pos.cash.transfer'
    _description = 'POS Cash Transfer'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True)

    from_session_id = fields.Many2one(
        'pos.session', string='From POS Session', required=True)
    to_session_id = fields.Many2one(
        'pos.session', string='To POS Session', required=True)
    from_config_id = fields.Many2one(
        'pos.config', string='From POS',
        related='from_session_id.config_id', store=True, readonly=True)
    to_config_id = fields.Many2one(
        'pos.config', string='To POS',
        related='to_session_id.config_id', store=True, readonly=True)

    amount = fields.Float(string='Amount', required=True, digits='Account')
    reason = fields.Char(string='Reason', required=True)
    transfer_date = fields.Datetime(
        string='Transfer Date', default=fields.Datetime.now, readonly=True)
    journal_id = fields.Many2one(
        'account.journal', string='Cash Journal', required=True,
        domain=[('type', '=', 'cash')])
    user_id = fields.Many2one(
        'res.users', string='Transferred By',
        default=lambda self: self.env.user, readonly=True)
    note = fields.Text(string='Notes')
    currency_id = fields.Many2one(
        'res.currency', related='from_session_id.currency_id', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pos.cash.transfer') or _('New')
        return super().create(vals_list)

    @api.constrains('from_session_id', 'to_session_id')
    def _check_sessions(self):
        for rec in self:
            if rec.from_session_id == rec.to_session_id:
                raise ValidationError(
                    _('Source and destination POS sessions must be different.'))

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(
                    _('Transfer amount must be greater than zero.'))

    def _get_cash_journal(self, session):
        """Get the first cash journal configured on this POS session."""
        for pm in session.config_id.payment_method_ids:
            if pm.journal_id and pm.journal_id.type == 'cash':
                return pm.journal_id
        return False

    def _create_statement_line(self, session, journal, amount, reason):
        """
        Create a cash in/out statement line on the POS session.
        In Odoo 19, account.bank.statement.line has pos_session_id directly
        (confirmed from pos_session.py line 80).
        """
        self.env['account.bank.statement.line'].create({
            'pos_session_id': session.id,
            'journal_id': journal.id,
            'amount': amount,
            'payment_ref': reason,
            'date': fields.Date.context_today(self),
        })

    def action_confirm_transfer(self):
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_('Only draft transfers can be confirmed.'))
        if self.from_session_id.state != 'opened':
            raise UserError(_('Source POS session is not open.'))
        if self.to_session_id.state != 'opened':
            raise UserError(_('Destination POS session is not open.'))

        from_journal = self._get_cash_journal(self.from_session_id)
        to_journal = self._get_cash_journal(self.to_session_id)

        if not from_journal:
            raise UserError(
                _('No cash journal found for source POS: %s') % self.from_config_id.name)
        if not to_journal:
            raise UserError(
                _('No cash journal found for destination POS: %s') % self.to_config_id.name)

        reason_out = _('[%s] Cash OUT → %s | %s') % (
            self.name, self.to_config_id.name, self.reason)
        reason_in = _('[%s] Cash IN ← %s | %s') % (
            self.name, self.from_config_id.name, self.reason)

        # Deduct from source POS (negative = cash out)
        self._create_statement_line(
            self.from_session_id, from_journal, -self.amount, reason_out)

        # Add to destination POS (positive = cash in)
        self._create_statement_line(
            self.to_session_id, to_journal, self.amount, reason_in)

        self.write({
            'state': 'done',
            'transfer_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Completed transfers cannot be cancelled.'))
        self.write({'state': 'cancelled'})
