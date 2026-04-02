from odoo import models, fields, api, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    cash_transfer_out_ids = fields.One2many(
        'pos.cash.transfer',
        'from_session_id',
        string='Cash Transfers Out',
    )
    cash_transfer_in_ids = fields.One2many(
        'pos.cash.transfer',
        'to_session_id',
        string='Cash Transfers In',
    )
    cash_transfer_out_count = fields.Integer(
        string='Transfers Out',
        compute='_compute_transfer_counts',
    )
    cash_transfer_in_count = fields.Integer(
        string='Transfers In',
        compute='_compute_transfer_counts',
    )
    total_cash_transferred_out = fields.Float(
        string='Total Transferred Out',
        compute='_compute_transfer_totals',
        digits='Account',
    )
    total_cash_transferred_in = fields.Float(
        string='Total Transferred In',
        compute='_compute_transfer_totals',
        digits='Account',
    )

    @api.depends('cash_transfer_out_ids', 'cash_transfer_in_ids')
    def _compute_transfer_counts(self):
        for session in self:
            session.cash_transfer_out_count = len(
                session.cash_transfer_out_ids.filtered(lambda t: t.state == 'done')
            )
            session.cash_transfer_in_count = len(
                session.cash_transfer_in_ids.filtered(lambda t: t.state == 'done')
            )

    @api.depends('cash_transfer_out_ids.amount', 'cash_transfer_out_ids.state',
                 'cash_transfer_in_ids.amount', 'cash_transfer_in_ids.state')
    def _compute_transfer_totals(self):
        for session in self:
            done_out = session.cash_transfer_out_ids.filtered(lambda t: t.state == 'done')
            done_in = session.cash_transfer_in_ids.filtered(lambda t: t.state == 'done')
            session.total_cash_transferred_out = sum(done_out.mapped('amount'))
            session.total_cash_transferred_in = sum(done_in.mapped('amount'))

    def action_open_cash_transfer_wizard(self):
        """Open the cash transfer wizard from the POS session."""
        self.ensure_one()
        return {
            'name': _('Transfer Cash to Another POS'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_from_session_id': self.id,
            },
        }

    def action_view_transfers_out(self):
        self.ensure_one()
        return {
            'name': _('Cash Transfers Out'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.transfer',
            'view_mode': 'list,form',
            'domain': [('from_session_id', '=', self.id)],
        }

    def action_view_transfers_in(self):
        self.ensure_one()
        return {
            'name': _('Cash Transfers In'),
            'type': 'ir.actions.act_window',
            'res_model': 'pos.cash.transfer',
            'view_mode': 'list,form',
            'domain': [('to_session_id', '=', self.id)],
        }
