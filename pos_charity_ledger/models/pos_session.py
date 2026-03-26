# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    charity_donation_total = fields.Float(
        string='Total Charity Donations',
        compute='_compute_charity_totals',
        store=True,
    )
    charity_donation_count = fields.Integer(
        string='Number of Donations',
        compute='_compute_charity_totals',
        store=True,
    )
    # Accumulated charity amount across all orders in this session.
    # Posted to the ledger as a single entry when the register is closed.
    charity_pending_amount = fields.Float(
        string='Pending Charity Amount',
        default=0.0,
        help='Accumulated charity donations from orders in this session, '
             'posted to the Charity Account only when the register is closed.',
    )

    @api.depends('order_ids')
    def _compute_charity_totals(self):
        for session in self:
            donations = self.env['pos.charity.donation'].search([
                ('pos_session_id', '=', session.id),
                ('state', '=', 'confirmed'),
            ])
            session.charity_donation_total = sum(donations.mapped('amount'))
            session.charity_donation_count = len(donations)

    def add_charity_pending_amount(self, amount):
        """
        Accumulate charity amount on the session.
        Called from pos_order.py (_process_order) each time an order
        with a charity donation is posted to the server.
        """
        self.ensure_one()
        self.charity_pending_amount = round(
            (self.charity_pending_amount or 0.0) + amount, 2
        )
        _logger.info(
            'Session %s: charity_pending_amount updated to %s',
            self.name, self.charity_pending_amount,
        )
        return self.charity_pending_amount

    # ── Posting logic ────────────────────────────────────────────────────────

    def _post_charity_donation_on_close(self):
        """
        Called when the session is closed (from any code path).
        Creates a single confirmed PosCharityDonation record and an
        accounting journal entry for the entire session's pending charity total.
        """
        self.ensure_one()
        amount = self.charity_pending_amount or 0.0
        if amount <= 0:
            return

        config = self.config_id
        if not config.charity_enabled or not config.charity_account_id:
            _logger.info(
                'Charity not enabled or no account configured — skipping for session %s',
                self.name,
            )
            return

        try:
            donation = self.env['pos.charity.donation'].create({
                'charity_account_id': config.charity_account_id.id,
                'pos_session_id': self.id,
                'amount': amount,
                'cashier_id': self.env.user.id,
                'state': 'confirmed',
                'note': 'Session close — total charity donations for %s' % self.name,
            })
            _logger.info(
                'Charity donation %s of %s created for session %s on close',
                donation.name, amount, self.name,
            )
        except Exception as exc:
            _logger.error(
                'Failed to create session charity donation for %s: %s',
                self.name, exc,
            )
            return

        self._create_session_charity_journal_entry(amount)

    def _create_session_charity_journal_entry(self, amount):
        """Accounting journal entry for the session charity total."""
        self.ensure_one()
        config = self.config_id
        if not config.charity_gl_account_id:
            _logger.info(
                'No charity GL account — skipping journal entry for session %s',
                self.name,
            )
            return
        try:
            journal = config.charity_journal_id or config.journal_id
            if not journal:
                _logger.error('No journal found for charity entry on session %s', self.name)
                return

            debit_account = journal.default_account_id
            if not debit_account:
                _logger.error('Could not determine debit account for session %s', self.name)
                return

            credit_account = config.charity_gl_account_id
            currency = self.currency_id or self.env.company.currency_id

            move_vals = {
                'journal_id': journal.id,
                'date': fields.Date.today(),
                'ref': 'Charity Donation — Session %s' % self.name,
                'line_ids': [
                    (0, 0, {
                        'name': 'Charity Donation — Session %s' % self.name,
                        'account_id': debit_account.id,
                        'debit': amount,
                        'credit': 0.0,
                        'currency_id': currency.id,
                    }),
                    (0, 0, {
                        'name': 'Charity Donation — Session %s' % self.name,
                        'account_id': credit_account.id,
                        'debit': 0.0,
                        'credit': amount,
                        'currency_id': currency.id,
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            _logger.info(
                'Charity journal entry %s created for session %s',
                move.name, self.name,
            )
        except Exception as exc:
            _logger.error(
                'Failed to create charity journal entry for session %s: %s',
                self.name, exc,
            )

    # ── Hooks into session-closing code paths ────────────────────────────────

    def action_pos_session_closing_control(self):
        """Backend 'Close Register' button path."""
        res = super().action_pos_session_closing_control()
        self._post_charity_donation_on_close()
        return res

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        """
        POS-UI 'Close Register' button path (Odoo 17/18/19 CE).
        This is the method called when the cashier clicks Close Register
        inside the POS interface.
        """
        res = super().close_session_from_ui(
            bank_payment_method_diff_pairs=bank_payment_method_diff_pairs
        )
        self._post_charity_donation_on_close()
        return res

    # ── POS UI data loaders ──────────────────────────────────────────────────

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        result['search_params']['fields'].extend([
            'charity_enabled',
            'charity_account_id',
            'charity_button_label',
            'charity_gl_account_id',
            'charity_journal_id',
        ])
        return result

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append('pos.charity.account')
        return result

    def _loader_params_pos_charity_account(self):
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['name', 'description'],
            }
        }
