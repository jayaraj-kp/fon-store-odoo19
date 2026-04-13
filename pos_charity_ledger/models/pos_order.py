# from odoo import models, fields
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class PosOrder(models.Model):
#     _inherit = 'pos.order'
#
#     charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
#     charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
#     charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)
#     charity_move_id = fields.Many2one('account.move', string='Charity Journal Entry', readonly=True)
#
#     def _process_order(self, order, existing_order):
#         """
#         Intercept charity metadata sent from the frontend before calling super().
#
#         The frontend sends:
#           order['charity_donation_amount']  — e.g. 3.0
#           order['charity_account_id']       — e.g. 1
#
#         The order total already includes the donation (because the JS bumped
#         the line price_unit via setUnitPrice before serialising).
#         We record the charity ledger here and defer the journal split to
#         session close via pos_session._create_pending_charity_journal_entries.
#         """
#         charity_amount     = float(order.get('charity_donation_amount') or 0.0)
#         charity_account_id = order.get('charity_account_id') or False
#
#         order_id  = super()._process_order(order, existing_order)
#         pos_order = self.browse(order_id)
#
#         if not pos_order.exists():
#             return order_id
#
#         # Fall back to the POS config's default charity account if none sent
#         if not charity_account_id and pos_order.config_id.charity_account_id:
#             charity_account_id = pos_order.config_id.charity_account_id.id
#
#         if charity_amount > 0 and charity_account_id:
#             pos_order.write({
#                 'charity_donation_amount': charity_amount,
#                 'charity_account_id':      charity_account_id,
#             })
#             pos_order._create_charity_donation()
#
#         return order_id
#
#     def _create_charity_donation(self):
#         """
#         Create the donation ledger record (pos.charity.donation).
#         Journal entry split is handled at session close.
#         """
#         self.ensure_one()
#         if not (self.charity_donation_amount > 0 and self.charity_account_id):
#             return
#         if self.charity_donation_id:
#             return  # already created (re-validation guard)
#         try:
#             donation = self.env['pos.charity.donation'].create({
#                 'charity_account_id': self.charity_account_id.id,
#                 'pos_session_id':     self.session_id.id,
#                 'pos_order_id':       self.id,
#                 'amount':             self.charity_donation_amount,
#                 'cashier_id':         self.user_id.id,
#                 'state':              'confirmed',
#                 'note':               'Donation from POS Order %s' % self.name,
#             })
#             self.charity_donation_id = donation.id
#             _logger.info(
#                 'Charity donation %.2f recorded for order %s',
#                 self.charity_donation_amount, self.name,
#             )
#         except Exception as e:
#             _logger.error('Failed to create charity donation record: %s', e)
#
#     # ------------------------------------------------------------------
#     # APPROACH: Amend the invoice payment move (POSS/0001) at session
#     # close to embed the charity split directly inside it.
#     #
#     # TARGET — what the accountant wants to see in POSS/0001:
#     #
#     #   Dr. 101300  AR (PoS)              ₹650   ← full cash received
#     #       Cr. 121000  AR (Customer)          ₹647   ← net invoice amount
#     #       Cr. 201002  Charity                ₹3     ← charity portion
#     #
#     # HOW: At session close we find the reconciliation move that was
#     # auto-created by Odoo for this order's invoice payment, temporarily
#     # reset it to draft, reduce the AR credit line by ₹3, add a new
#     # Charity credit line for ₹3, then re-post it.
#     # ------------------------------------------------------------------
#     def _create_charity_journal_entry(self):
#         """
#         Called by pos_session._create_pending_charity_journal_entries
#         at register close time.
#
#         Instead of creating a NEW separate entry, we AMEND the existing
#         invoice payment move (POSS/0001) so the charity split appears
#         inside it as a three-line entry.
#         """
#         self.ensure_one()
#
#         if self.charity_move_id:
#             return  # already processed
#
#         config = self.config_id
#         if not config.charity_gl_account_id:
#             _logger.info(
#                 'No charity GL account configured — skipping charity entry for order %s',
#                 self.name,
#             )
#             return
#
#         charity_amount  = self.charity_donation_amount
#         charity_account = config.charity_gl_account_id
#         currency        = self.currency_id or self.env.company.currency_id
#
#         # ------------------------------------------------------------------
#         # Step 1: Find the invoice payment reconciliation move (POSS/0001).
#         # In Odoo 17/19 CE the move is linked via account.payment or
#         # account.move that references this order's invoice.
#         # We search for a posted move in the POS journal whose reference
#         # matches the session/order invoice payment.
#         # ------------------------------------------------------------------
#         payment_move = self._find_invoice_payment_move()
#
#         if payment_move:
#             # ── PREFERRED PATH: amend POSS/0001 ──────────────────────────
#             try:
#                 # Find the AR (Customer) / receivable credit line
#                 # (the line that reconciles the invoice — credit > 0,
#                 #  account type is asset_receivable or liability_payable)
#                 ar_credit_line = payment_move.line_ids.filtered(
#                     lambda l: l.credit > 0
#                     and l.account_id.account_type in ('asset_receivable', 'liability_payable')
#                 )
#
#                 if not ar_credit_line:
#                     _logger.warning(
#                         'No receivable credit line found in move %s — falling back to separate entry',
#                         payment_move.name,
#                     )
#                     self._create_standalone_charity_entry(charity_amount, charity_account,
#                                                           currency, config)
#                     return
#
#                 # Take the first matching line (there should only be one)
#                 ar_credit_line = ar_credit_line[0]
#
#                 # Temporarily unlock the posted move
#                 payment_move.button_draft()
#
#                 # Reduce the AR credit by the charity amount (₹650 → ₹647)
#                 ar_credit_line.with_context(check_move_validity=False).write({
#                     'credit': ar_credit_line.credit - charity_amount,
#                 })
#
#                 # Add the Charity credit line (₹3)
#                 self.env['account.move.line'].with_context(
#                     check_move_validity=False
#                 ).create({
#                     'move_id':     payment_move.id,
#                     'name':        'Charity Donation - %s' % self.name,
#                     'account_id':  charity_account.id,
#                     'debit':       0.0,
#                     'credit':      charity_amount,
#                     'currency_id': currency.id,
#                 })
#
#                 # Re-post the amended move
#                 payment_move.action_post()
#
#                 # Link so we don't process this order again
#                 self.charity_move_id = payment_move.id
#
#                 _logger.info(
#                     'Charity split (%.2f) embedded into payment move %s for order %s | '
#                     'AR credit reduced to %.2f, Charity GL %s credited %.2f',
#                     charity_amount, payment_move.name, self.name,
#                     ar_credit_line.credit, charity_account.code, charity_amount,
#                 )
#
#             except Exception as e:
#                 _logger.error(
#                     'Failed to amend payment move %s for order %s: %s',
#                     payment_move.name, self.name, e,
#                 )
#                 # Always ensure the move ends up posted even on error
#                 try:
#                     if payment_move.state == 'draft':
#                         payment_move.action_post()
#                 except Exception:
#                     pass
#                 # Fall back to a separate entry so accounting stays complete
#                 self._create_standalone_charity_entry(charity_amount, charity_account,
#                                                       currency, config)
#         else:
#             # ── FALLBACK PATH: create a standalone entry ──────────────────
#             _logger.warning(
#                 'Could not locate invoice payment move for order %s — '
#                 'creating standalone charity entry.',
#                 self.name,
#             )
#             self._create_standalone_charity_entry(charity_amount, charity_account,
#                                                   currency, config)
#
#     def _find_invoice_payment_move(self):
#         """
#         Locate the invoice payment reconciliation move (POSS/nnnn) that
#         Odoo created when the customer invoice for this POS order was paid.
#
#         Search strategy (most specific → least specific):
#           1. Moves linked via account.payment to this order's invoice
#           2. Posted moves in the POS journal whose ref contains the order name
#         """
#         self.ensure_one()
#
#         # Strategy 1: via the invoice's payment_ids
#         invoice = self.account_move
#         if invoice:
#             for payment in invoice._get_reconciled_payments():
#                 if payment.move_id and payment.move_id.state == 'posted':
#                     return payment.move_id
#
#         # Strategy 2: search by reference in the POS journal
#         journal = self.config_id.journal_id
#         if journal and self.name:
#             move = self.env['account.move'].search([
#                 ('journal_id', '=', journal.id),
#                 ('state',      '=', 'posted'),
#                 ('ref',        'like', self.name),
#                 ('move_type',  '=', 'entry'),
#             ], limit=1)
#             if move:
#                 return move
#
#         return None
#
#     def _create_standalone_charity_entry(self, charity_amount, charity_account,
#                                          currency, config):
#         """
#         Fallback: create a standalone charity journal entry when we cannot
#         amend the payment move.
#
#         Entry:
#             Dr. 400000  Product Sales   ₹3   (reduce revenue)
#             Cr. 201002  Charity         ₹3
#         """
#         try:
#             journal = config.charity_journal_id or config.journal_id
#             if not journal:
#                 _logger.error('No journal for standalone charity entry on order %s', self.name)
#                 return
#
#             # Debit: Product Sales
#             debit_account = False
#             for line in self.lines:
#                 account = (
#                     line.product_id.property_account_income_id
#                     or line.product_id.categ_id.property_account_income_categ_id
#                 )
#                 if account:
#                     debit_account = account
#                     break
#             if not debit_account and config.journal_id:
#                 debit_account = config.journal_id.default_account_id
#             if not debit_account:
#                 _logger.error('No debit account for standalone charity entry on order %s', self.name)
#                 return
#
#             move = self.env['account.move'].create({
#                 'journal_id': journal.id,
#                 'date':       self.date_order.date() if self.date_order else fields.Date.today(),
#                 'ref':        'Charity Donation - %s' % self.name,
#                 'line_ids': [
#                     (0, 0, {
#                         'name':        'Charity Donation - %s' % self.name,
#                         'account_id':  debit_account.id,
#                         'debit':       charity_amount,
#                         'credit':      0.0,
#                         'currency_id': currency.id,
#                     }),
#                     (0, 0, {
#                         'name':        'Charity Donation - %s' % self.name,
#                         'account_id':  charity_account.id,
#                         'debit':       0.0,
#                         'credit':      charity_amount,
#                         'currency_id': currency.id,
#                     }),
#                 ],
#             })
#             move.action_post()
#             self.charity_move_id = move.id
#             _logger.info(
#                 'Standalone charity entry %s (%.2f) posted for order %s',
#                 move.name, charity_amount, self.name,
#             )
#         except Exception as e:
#             _logger.error(
#                 'Failed to create standalone charity entry for order %s: %s',
#                 self.name, e,
#             )
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
    charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
    charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)
    charity_move_id = fields.Many2one('account.move', string='Charity Journal Entry', readonly=True)

    def _process_order(self, order, existing_order):
        """
        Intercept charity metadata sent from the frontend before calling super().

        The frontend sends:
          order['charity_donation_amount']  — e.g. 3.0
          order['charity_account_id']       — e.g. 1

        The order total already includes the donation (because the JS bumped
        the line price_unit via setUnitPrice before serialising).
        We record the charity ledger here and defer the journal split to
        session close via pos_session._create_pending_charity_journal_entries.
        """
        charity_amount     = float(order.get('charity_donation_amount') or 0.0)
        charity_account_id = order.get('charity_account_id') or False

        order_id  = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)

        if not pos_order.exists():
            return order_id

        # Fall back to the POS config's default charity account if none sent
        if not charity_account_id and pos_order.config_id.charity_account_id:
            charity_account_id = pos_order.config_id.charity_account_id.id

        if charity_amount > 0 and charity_account_id:
            pos_order.write({
                'charity_donation_amount': charity_amount,
                'charity_account_id':      charity_account_id,
            })
            pos_order._create_charity_donation()

        return order_id

    def _create_charity_donation(self):
        """
        Create the donation ledger record (pos.charity.donation).
        Journal entry split is handled at session close.
        """
        self.ensure_one()
        if not (self.charity_donation_amount > 0 and self.charity_account_id):
            return
        if self.charity_donation_id:
            return  # already created (re-validation guard)
        try:
            donation = self.env['pos.charity.donation'].create({
                'charity_account_id': self.charity_account_id.id,
                'pos_session_id':     self.session_id.id,
                'pos_order_id':       self.id,
                'amount':             self.charity_donation_amount,
                'cashier_id':         self.user_id.id,
                'state':              'confirmed',
                'note':               'Donation from POS Order %s' % self.name,
            })
            self.charity_donation_id = donation.id
            _logger.info(
                'Charity donation %.2f recorded for order %s',
                self.charity_donation_amount, self.name,
            )
        except Exception as e:
            _logger.error('Failed to create charity donation record: %s', e)

    # ------------------------------------------------------------------
    # APPROACH: Amend the invoice payment move (POSS/0001) at session
    # close to embed the charity split directly inside it.
    #
    # TARGET — what the accountant wants to see in POSS/0001:
    #
    #   Dr. 101300  AR (PoS)              ₹650   ← full cash received
    #       Cr. 121000  AR (Customer)          ₹647   ← net invoice amount
    #       Cr. 201002  Charity                ₹3     ← charity portion
    #
    # HOW: At session close we find the reconciliation move that was
    # auto-created by Odoo for this order's invoice payment, temporarily
    # reset it to draft, reduce the AR credit line by ₹3, add a new
    # Charity credit line for ₹3, then re-post it.
    # ------------------------------------------------------------------
    def _create_charity_journal_entry(self):
        """
        Called by pos_session._create_pending_charity_journal_entries
        at register close time.

        Instead of creating a NEW separate entry, we AMEND the existing
        invoice payment move (POSS/0001) so the charity split appears
        inside it as a three-line entry.
        """
        self.ensure_one()

        if self.charity_move_id:
            return  # already processed

        config = self.config_id
        if not config.charity_gl_account_id:
            _logger.info(
                'No charity GL account configured — skipping charity entry for order %s',
                self.name,
            )
            return

        charity_amount  = self.charity_donation_amount
        charity_account = config.charity_gl_account_id
        currency        = self.currency_id or self.env.company.currency_id

        # ------------------------------------------------------------------
        # Step 1: Find the invoice payment reconciliation move (POSS/0001).
        # In Odoo 17/19 CE the move is linked via account.payment or
        # account.move that references this order's invoice.
        # We search for a posted move in the POS journal whose reference
        # matches the session/order invoice payment.
        # ------------------------------------------------------------------
        payment_move = self._find_invoice_payment_move()

        if payment_move:
            # ── PREFERRED PATH: amend POSS/0001 ──────────────────────────
            try:
                # Find the AR (Customer) / receivable credit line
                # (the line that reconciles the invoice — credit > 0,
                #  account type is asset_receivable or liability_payable)
                ar_credit_line = payment_move.line_ids.filtered(
                    lambda l: l.credit > 0
                    and l.account_id.account_type in ('asset_receivable', 'liability_payable')
                )

                if not ar_credit_line:
                    _logger.warning(
                        'No receivable credit line found in move %s — falling back to separate entry',
                        payment_move.name,
                    )
                    self._create_standalone_charity_entry(charity_amount, charity_account,
                                                          currency, config)
                    return

                # Take the first matching line (there should only be one)
                ar_credit_line = ar_credit_line[0]

                # Temporarily unlock the posted move
                payment_move.button_draft()

                # Reduce the AR credit by the charity amount (₹650 → ₹647)
                ar_credit_line.with_context(check_move_validity=False).write({
                    'credit': ar_credit_line.credit - charity_amount,
                })

                # Add the Charity credit line (₹3) with partner_id
                self.env['account.move.line'].with_context(
                    check_move_validity=False
                ).create({
                    'move_id':     payment_move.id,
                    'name':        'Charity Donation - %s' % self.name,
                    'account_id':  charity_account.id,
                    'partner_id':  self.partner_id.id,
                    'debit':       0.0,
                    'credit':      charity_amount,
                    'currency_id': currency.id,
                })

                # Re-post the amended move
                payment_move.action_post()

                # Link so we don't process this order again
                self.charity_move_id = payment_move.id

                _logger.info(
                    'Charity split (%.2f) embedded into payment move %s for order %s | '
                    'AR credit reduced to %.2f, Charity GL %s credited %.2f',
                    charity_amount, payment_move.name, self.name,
                    ar_credit_line.credit, charity_account.code, charity_amount,
                )

            except Exception as e:
                _logger.error(
                    'Failed to amend payment move %s for order %s: %s',
                    payment_move.name, self.name, e,
                )
                # Always ensure the move ends up posted even on error
                try:
                    if payment_move.state == 'draft':
                        payment_move.action_post()
                except Exception:
                    pass
                # Fall back to a separate entry so accounting stays complete
                self._create_standalone_charity_entry(charity_amount, charity_account,
                                                      currency, config)
        else:
            # ── FALLBACK PATH: create a standalone entry ──────────────────
            _logger.warning(
                'Could not locate invoice payment move for order %s — '
                'creating standalone charity entry.',
                self.name,
            )
            self._create_standalone_charity_entry(charity_amount, charity_account,
                                                  currency, config)

    def _find_invoice_payment_move(self):
        """
        Locate the invoice payment reconciliation move (POSS/nnnn) that
        Odoo created when the customer invoice for this POS order was paid.

        Search strategy (most specific → least specific):
          1. Moves linked via account.payment to this order's invoice
          2. Posted moves in the POS journal whose ref contains the order name
        """
        self.ensure_one()

        # Strategy 1: via the invoice's payment_ids
        invoice = self.account_move
        if invoice:
            for payment in invoice._get_reconciled_payments():
                if payment.move_id and payment.move_id.state == 'posted':
                    return payment.move_id

        # Strategy 2: search by reference in the POS journal
        journal = self.config_id.journal_id
        if journal and self.name:
            move = self.env['account.move'].search([
                ('journal_id', '=', journal.id),
                ('state',      '=', 'posted'),
                ('ref',        'like', self.name),
                ('move_type',  '=', 'entry'),
            ], limit=1)
            if move:
                return move

        return None

    def _create_standalone_charity_entry(self, charity_amount, charity_account,
                                         currency, config):
        """
        Fallback: create a standalone charity journal entry when we cannot
        amend the payment move.

        Entry:
            Dr. 400000  Product Sales   ₹3   (reduce revenue)
            Cr. 201002  Charity         ₹3
        """
        try:
            journal = config.charity_journal_id or config.journal_id
            if not journal:
                _logger.error('No journal for standalone charity entry on order %s', self.name)
                return

            # Debit: Product Sales
            debit_account = False
            for line in self.lines:
                account = (
                    line.product_id.property_account_income_id
                    or line.product_id.categ_id.property_account_income_categ_id
                )
                if account:
                    debit_account = account
                    break
            if not debit_account and config.journal_id:
                debit_account = config.journal_id.default_account_id
            if not debit_account:
                _logger.error('No debit account for standalone charity entry on order %s', self.name)
                return

            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date':       self.date_order.date() if self.date_order else fields.Date.today(),
                'ref':        'Charity Donation - %s' % self.name,
                'line_ids': [
                    (0, 0, {
                        'name':        'Charity Donation - %s' % self.name,
                        'account_id':  debit_account.id,
                        'partner_id':  self.partner_id.id,
                        'debit':       charity_amount,
                        'credit':      0.0,
                        'currency_id': currency.id,
                    }),
                    (0, 0, {
                        'name':        'Charity Donation - %s' % self.name,
                        'account_id':  charity_account.id,
                        'partner_id':  self.partner_id.id,
                        'debit':       0.0,
                        'credit':      charity_amount,
                        'currency_id': currency.id,
                    }),
                ],
            })
            move.action_post()
            self.charity_move_id = move.id
            _logger.info(
                'Standalone charity entry %s (%.2f) posted for order %s',
                move.name, charity_amount, self.name,
            )
        except Exception as e:
            _logger.error(
                'Failed to create standalone charity entry for order %s: %s',
                self.name, e,
            )