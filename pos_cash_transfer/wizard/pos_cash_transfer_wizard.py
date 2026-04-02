from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class PosCashTransferWizard(models.TransientModel):
    _name = 'pos.cash.transfer.wizard'
    _description = 'POS Cash Transfer Wizard'

    from_session_id = fields.Many2one(
        'pos.session',
        string='From POS Session',
        required=True,
        domain=[('state', '=', 'opened')],
    )
    from_config_id = fields.Many2one(
        'pos.config',
        string='From POS',
        related='from_session_id.config_id',
        readonly=True,
    )
    to_session_id = fields.Many2one(
        'pos.session',
        string='To POS Session',
        required=True,
        domain=[('state', '=', 'opened')],
    )
    to_config_id = fields.Many2one(
        'pos.config',
        string='To POS',
        related='to_session_id.config_id',
        readonly=True,
    )
    amount = fields.Float(
        string='Amount to Transfer',
        required=True,
        digits='Account',
    )
    reason = fields.Char(
        string='Reason',
        required=True,
        default='Cash Transfer',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Cash Journal',
        required=True,
        domain=[('type', '=', 'cash')],
        compute='_compute_journal_id',
        store=True,
        readonly=False,
        help='The cash journal of the source POS',
    )
    available_cash = fields.Float(
        string='Available Cash (Approx.)',
        compute='_compute_available_cash',
    )
    note = fields.Text(string='Notes')

    @api.depends('from_session_id')
    def _compute_journal_id(self):
        for rec in self:
            journal = False
            if rec.from_session_id:
                for pm in rec.from_session_id.config_id.payment_method_ids:
                    if pm.journal_id and pm.journal_id.type == 'cash':
                        journal = pm.journal_id
                        break
            rec.journal_id = journal

    @api.depends('from_session_id')
    def _compute_available_cash(self):
        for rec in self:
            if rec.from_session_id:
                # Sum of cash in/out statement lines for this session
                session = rec.from_session_id
                rec.available_cash = session.cash_register_balance_start + \
                    sum(session.statement_line_ids.filtered(
                        lambda l: l.journal_id.type == 'cash'
                    ).mapped('amount'))
            else:
                rec.available_cash = 0.0

    @api.constrains('from_session_id', 'to_session_id')
    def _check_different_sessions(self):
        for rec in self:
            if rec.from_session_id and rec.to_session_id:
                if rec.from_session_id == rec.to_session_id:
                    raise ValidationError(_('Source and destination sessions must be different.'))

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Amount must be greater than zero.'))

    def action_transfer(self):
        """Create and confirm the cash transfer."""
        self.ensure_one()

        if not self.journal_id:
            raise UserError(_('Please select a cash journal for the transfer.'))

        transfer = self.env['pos.cash.transfer'].create({
            'from_session_id': self.from_session_id.id,
            'to_session_id': self.to_session_id.id,
            'amount': self.amount,
            'reason': self.reason,
            'journal_id': self.journal_id.id,
            'note': self.note,
        })

        result = transfer.action_confirm_transfer()

        # Return the transfer record view
        return {
            'name': _('Cash Transfer'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.transfer',
            'res_id': transfer.id,
            'view_mode': 'form',
            'target': 'current',
        }
