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
    ], string='Status', default='draft', readonly=True, tracking=True)

    from_session_id = fields.Many2one(
        'pos.session',
        string='From POS Session',
        required=True,
        domain=[('state', 'in', ['opened'])],
        help='Source POS session to transfer cash from',
    )
    to_session_id = fields.Many2one(
        'pos.session',
        string='To POS Session',
        required=True,
        domain=[('state', 'in', ['opened'])],
        help='Destination POS session to transfer cash to',
    )
    from_config_id = fields.Many2one(
        'pos.config',
        string='From POS',
        related='from_session_id.config_id',
        store=True,
        readonly=True,
    )
    to_config_id = fields.Many2one(
        'pos.config',
        string='To POS',
        related='to_session_id.config_id',
        store=True,
        readonly=True,
    )
    amount = fields.Float(
        string='Amount',
        required=True,
        digits='Account',
    )
    reason = fields.Char(
        string='Reason',
        required=True,
    )
    transfer_date = fields.Datetime(
        string='Transfer Date',
        default=fields.Datetime.now,
        readonly=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Transfer Journal',
        required=True,
        domain=[('type', 'in', ['cash'])],
        help='Intermediary journal for the transfer (usually a Cash or Transit journal)',
    )
    move_out_id = fields.Many2one(
        'account.move',
        string='Journal Entry (Out)',
        readonly=True,
        copy=False,
    )
    move_in_id = fields.Many2one(
        'account.move',
        string='Journal Entry (In)',
        readonly=True,
        copy=False,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Transferred By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    note = fields.Text(string='Notes')
    currency_id = fields.Many2one(
        'res.currency',
        related='from_session_id.currency_id',
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.cash.transfer') or _('New')
        return super().create(vals_list)

    @api.constrains('from_session_id', 'to_session_id')
    def _check_sessions(self):
        for rec in self:
            if rec.from_session_id == rec.to_session_id:
                raise ValidationError(_('Source and destination POS sessions must be different.'))

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Transfer amount must be greater than zero.'))

    def action_confirm_transfer(self):
        """Confirm the cash transfer and create journal entries."""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(_('Only draft transfers can be confirmed.'))

        if self.from_session_id.state != 'opened':
            raise UserError(_('Source POS session is not open.'))

        if self.to_session_id.state != 'opened':
            raise UserError(_('Destination POS session is not open.'))

        # Get the cash journals from each POS config
        from_journal = self._get_cash_journal(self.from_session_id)
        to_journal = self._get_cash_journal(self.to_session_id)

        if not from_journal:
            raise UserError(_('No cash journal found for the source POS: %s') % self.from_config_id.name)
        if not to_journal:
            raise UserError(_('No cash journal found for the destination POS: %s') % self.to_config_id.name)

        # Create cash out statement line for source POS
        self._create_cash_statement_line(
            session=self.from_session_id,
            journal=from_journal,
            amount=-self.amount,
            reason=_('Cash Transfer Out to %s - %s') % (self.to_config_id.name, self.reason),
        )

        # Create cash in statement line for destination POS
        self._create_cash_statement_line(
            session=self.to_session_id,
            journal=to_journal,
            amount=self.amount,
            reason=_('Cash Transfer In from %s - %s') % (self.from_config_id.name, self.reason),
        )

        self.write({
            'state': 'done',
            'transfer_date': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cash Transfer Successful'),
                'message': _('%.2f transferred from %s to %s') % (
                    self.amount,
                    self.from_config_id.name,
                    self.to_config_id.name,
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Completed transfers cannot be cancelled.'))
        self.write({'state': 'cancelled'})

    def _get_cash_journal(self, session):
        """Get the cash journal for a POS session."""
        for payment_method in session.config_id.payment_method_ids:
            if payment_method.journal_id and payment_method.journal_id.type == 'cash':
                return payment_method.journal_id
        return False

    def _create_cash_statement_line(self, session, journal, amount, reason):
        """Create a cash in/out statement line on the POS session."""
        # In Odoo 17+/19, cash in/out is recorded via account.bank.statement.line
        # linked to the session's statement
        statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', journal.id),
            ('pos_session_id', '=', session.id),
        ], limit=1)

        if not statement:
            # Fallback: create directly as a cash move on session
            session._create_cash_statement_lines([{
                'amount': amount,
                'reason': reason,
            }])
        else:
            self.env['account.bank.statement.line'].create({
                'statement_id': statement.id,
                'journal_id': journal.id,
                'amount': amount,
                'payment_ref': reason,
                'date': fields.Date.today(),
            })
