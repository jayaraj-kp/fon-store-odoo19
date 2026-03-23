from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PosCashTransfer(models.Model):
    _name = 'pos.cash.transfer'
    _description = 'POS Cash Transfer Between Sessions'
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    from_session_id = fields.Many2one(
        'pos.session',
        string='From POS Session',
        required=True,
        domain=[('state', '=', 'opened')]
    )
    to_session_id = fields.Many2one(
        'pos.session',
        string='To POS Session',
        required=True,
        domain=[('state', '=', 'opened')]
    )
    from_pos_id = fields.Many2one(
        'pos.config',
        string='From Counter',
        related='from_session_id.config_id',
        store=True
    )
    to_pos_id = fields.Many2one(
        'pos.config',
        string='To Counter',
        related='to_session_id.config_id',
        store=True
    )
    amount = fields.Float(
        string='Transfer Amount',
        required=True,
        digits=(16, 2)
    )
    reason = fields.Text(
        string='Reason / Notes'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Transferred'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True)

    cashier_id = fields.Many2one(
        'res.users',
        string='Transferred By',
        default=lambda self: self.env.user,
        readonly=True
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Cash Journal',
        domain=[('type', '=', 'cash')]
    )
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    transfer_date = fields.Datetime(
        string='Transfer Date',
        default=fields.Datetime.now,
        readonly=True
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'pos.cash.transfer') or _('New')
        return super().create(vals)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Transfer amount must be greater than zero!'))

    @api.constrains('from_session_id', 'to_session_id')
    def _check_sessions(self):
        for rec in self:
            if rec.from_session_id == rec.to_session_id:
                raise ValidationError(_('From and To POS sessions cannot be the same!'))

    def action_transfer(self):
        """Process the cash transfer between POS sessions"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft transfers can be processed!'))

        if self.from_session_id.state != 'opened':
            raise UserError(_('Source POS session is not open!'))

        if self.to_session_id.state != 'opened':
            raise UserError(_('Destination POS session is not open!'))

        # Create cash out statement in source session
        self._create_cash_statement(
            self.from_session_id,
            -self.amount,
            _('Cash Transfer to %s - %s') % (
                self.to_pos_id.name, self.name)
        )

        # Create cash in statement in destination session
        self._create_cash_statement(
            self.to_session_id,
            self.amount,
            _('Cash Transfer from %s - %s') % (
                self.from_pos_id.name, self.name)
        )

        self.write({
            'state': 'done',
            'transfer_date': fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cash Transfer Successful!'),
                'message': _('₹ %.2f transferred from %s to %s') % (
                    self.amount,
                    self.from_pos_id.name,
                    self.to_pos_id.name
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_cash_statement(self, session, amount, reason):
        """Create cash in/out statement line for a session"""
        self.env['pos.payment'].create({
            'pos_order_id': False,
            'amount': amount,
            'session_id': session.id,
            'payment_method_id': session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1].id or
                session.config_id.payment_method_ids[:1].id,
        })

        # Create bank statement line
        bank_statement = session.statement_line_ids.filtered(
            lambda s: s.journal_id.type == 'cash')[:1]

        self.env['account.bank.statement.line'].create({
            'journal_id': session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1].journal_id.id,
            'amount': amount,
            'narration': reason,
            'date': fields.Date.today(),
            'pos_session_id': session.id,
        })

    def action_cancel(self):
        """Cancel the transfer"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel a completed transfer!'))
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})


class PosSession(models.Model):
    _inherit = 'pos.session'

    cash_transfer_out_ids = fields.One2many(
        'pos.cash.transfer',
        'from_session_id',
        string='Cash Transfers Out'
    )
    cash_transfer_in_ids = fields.One2many(
        'pos.cash.transfer',
        'to_session_id',
        string='Cash Transfers In'
    )
    cash_transfer_out_count = fields.Integer(
        compute='_compute_transfer_counts',
        string='Transfers Out'
    )
    cash_transfer_in_count = fields.Integer(
        compute='_compute_transfer_counts',
        string='Transfers In'
    )

    @api.depends('cash_transfer_out_ids', 'cash_transfer_in_ids')
    def _compute_transfer_counts(self):
        for session in self:
            session.cash_transfer_out_count = len(
                session.cash_transfer_out_ids.filtered(
                    lambda t: t.state == 'done'))
            session.cash_transfer_in_count = len(
                session.cash_transfer_in_ids.filtered(
                    lambda t: t.state == 'done'))

    @api.model
    def create_transfer_from_pos(self, from_session_id, to_session_id,
                                  amount, reason=''):
        """Called from POS JS to create a cash transfer"""
        try:
            from_session = self.env['pos.session'].browse(from_session_id)
            to_session = self.env['pos.session'].browse(to_session_id)

            if not from_session.exists() or not to_session.exists():
                return {'success': False, 'error': 'Session not found!'}
            if from_session.state != 'opened':
                return {'success': False, 'error': 'Source POS is not open!'}
            if to_session.state != 'opened':
                return {'success': False, 'error': 'Destination POS is not open!'}
            if float(amount) <= 0:
                return {'success': False, 'error': 'Amount must be greater than 0!'}

            transfer = self.create({
                'from_session_id': from_session_id,
                'to_session_id': to_session_id,
                'amount': float(amount),
                'reason': reason,
                'cashier_id': self.env.user.id,
            })

            from_cash = from_session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1]
            to_cash = to_session.config_id.payment_method_ids.filtered(
                lambda m: m.is_cash_count)[:1]

            if not from_cash or not to_cash:
                return {'success': False,
                        'error': 'Cash payment method not configured in one of the sessions!'}

            from_reason = 'Cash Transfer OUT to %s - %s' % (
                to_session.config_id.name, transfer.name)
            to_reason = 'Cash Transfer IN from %s - %s' % (
                from_session.config_id.name, transfer.name)
            if reason:
                from_reason += ' (%s)' % reason
                to_reason += ' (%s)' % reason

            self.env['account.bank.statement.line'].sudo().create([
                {
                    'journal_id': from_cash.journal_id.id,
                    'amount': -float(amount),
                    'narration': from_reason,
                    'date': fields.Date.today(),
                    'pos_session_id': from_session.id,
                },
                {
                    'journal_id': to_cash.journal_id.id,
                    'amount': float(amount),
                    'narration': to_reason,
                    'date': fields.Date.today(),
                    'pos_session_id': to_session.id,
                }
            ])

            transfer.write({'state': 'done'})

            return {
                'success': True,
                'transfer_id': transfer.id,
                'transfer_name': transfer.name,
                'message': 'Rs. %.2f successfully transferred to %s!' % (
                    float(amount), to_session.config_id.name)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class PosSessionTransfer(models.Model):
    _inherit = 'pos.session'

    @api.model
    def get_open_sessions_for_transfer(self, current_session_id):
        """Return all open POS sessions except current one — called from POS JS"""
        sessions = self.search([
            ('state', '=', 'opened'),
            ('id', '!=', current_session_id),
        ])
        return [{
            'id': s.id,
            'name': s.name,
            'pos_name': s.config_id.name,
            'cashier': s.user_id.name,
        } for s in sessions]
