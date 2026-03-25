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
    )
    to_session_id = fields.Many2one(
        'pos.session',
        string='To POS Session',
        required=True,
    )
    from_pos_id = fields.Many2one(
        'pos.config',
        string='From Counter',
        related='from_session_id.config_id',
        store=True,
        readonly=True,
    )
    to_pos_id = fields.Many2one(
        'pos.config',
        string='To Counter',
        related='to_session_id.config_id',
        store=True,
        readonly=True,
    )
    amount = fields.Float(
        string='Transfer Amount (Rs.)',
        required=True,
        digits=(16, 2)
    )
    reason = fields.Text(string='Reason / Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Transferred'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True)
    cashier_id = fields.Many2one(
        'res.users',
        string='Transferred By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    transfer_date = fields.Datetime(
        string='Transfer Date',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pos.cash.transfer') or _('New')
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(
                    _('Transfer amount must be greater than zero!'))

    @api.constrains('from_session_id', 'to_session_id')
    def _check_sessions(self):
        for rec in self:
            if rec.from_session_id == rec.to_session_id:
                raise ValidationError(
                    _('Source and destination POS cannot be the same!'))

    def action_transfer(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft transfers can be processed!'))
        self._do_transfer()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Successful!'),
                'message': _('Rs. %.2f transferred from %s to %s') % (
                    self.amount,
                    self.from_pos_id.name,
                    self.to_pos_id.name,
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _do_transfer(self):
        """
        Core transfer logic.
        Uses cash.box.out / cash.box.in wizards — compatible with
        Odoo 19 Community Edition without full Accounting module.
        """
        from_session = self.from_session_id
        to_session = self.to_session_id

        # Verify both sessions are still open
        if from_session.state != 'opened':
            raise UserError(_('Source POS session is no longer open!'))
        if to_session.state != 'opened':
            raise UserError(_('Destination POS session is no longer open!'))

        # Verify cash payment methods exist on both sides
        from_cash = from_session.config_id.payment_method_ids.filtered(
            lambda m: m.is_cash_count)[:1]
        to_cash = to_session.config_id.payment_method_ids.filtered(
            lambda m: m.is_cash_count)[:1]

        if not from_cash:
            raise UserError(
                _('No cash payment method configured on source POS: %s')
                % from_session.config_id.name)
        if not to_cash:
            raise UserError(
                _('No cash payment method configured on destination POS: %s')
                % to_session.config_id.name)

        note_out = 'Cash Transfer OUT → %s [%s]%s' % (
            to_session.config_id.name,
            self.name,
            (' | ' + self.reason) if self.reason else '',
        )
        note_in = 'Cash Transfer IN ← %s [%s]%s' % (
            from_session.config_id.name,
            self.name,
            (' | ' + self.reason) if self.reason else '',
        )

        # Take cash OUT of source session
        self.env['cash.box.out'].sudo().with_context(
            active_model='pos.session',
            active_ids=from_session.ids,
        ).create({
            'name': note_out,
            'amount': self.amount,
        }).run()

        # Put cash IN to destination session
        self.env['cash.box.in'].sudo().with_context(
            active_model='pos.session',
            active_ids=to_session.ids,
        ).create({
            'name': note_in,
            'amount': self.amount,
        }).run()

        self.write({
            'state': 'done',
            'transfer_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot cancel a completed transfer!'))
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def create_transfer_from_pos(self, from_session_id, to_session_id,
                                  amount, reason=''):
        """Called from POS JS via ORM to process a cash transfer."""
        try:
            from_session = self.env['pos.session'].sudo().browse(from_session_id)
            to_session = self.env['pos.session'].sudo().browse(to_session_id)

            if not from_session.exists():
                return {'success': False, 'error': 'Source session not found!'}
            if not to_session.exists():
                return {'success': False, 'error': 'Destination session not found!'}
            if from_session.state != 'opened':
                return {'success': False, 'error': 'Source POS is not open!'}
            if to_session.state != 'opened':
                return {'success': False, 'error': 'Destination POS is not open!'}
            if float(amount) <= 0:
                return {'success': False, 'error': 'Amount must be greater than 0!'}

            transfer = self.sudo().create({
                'from_session_id': from_session_id,
                'to_session_id': to_session_id,
                'amount': float(amount),
                'reason': reason or '',
                'cashier_id': self.env.user.id,
            })
            transfer._do_transfer()

            return {
                'success': True,
                'transfer_name': transfer.name,
                'message': 'Rs. %.2f transferred to %s successfully!' % (
                    float(amount), to_session.config_id.name),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class PosSession(models.Model):
    _inherit = 'pos.session'

    cash_transfer_out_ids = fields.One2many(
        'pos.cash.transfer', 'from_session_id', string='Cash Transfers Out')
    cash_transfer_in_ids = fields.One2many(
        'pos.cash.transfer', 'to_session_id', string='Cash Transfers In')

    @api.model
    def get_open_sessions_for_transfer(self, current_session_id):
        """
        Return all other open POS sessions.
        Called from POS JS via orm.call — uses sudo() so that
        employee-level POS users (PIN login) can also call this.
        """
        sessions = self.sudo().search([
            ('state', '=', 'opened'),
            ('id', '!=', current_session_id),
        ])
        return [{
            'id': s.id,
            'name': s.name,
            'pos_name': s.config_id.name,
            'cashier': s.user_id.name,
        } for s in sessions]
