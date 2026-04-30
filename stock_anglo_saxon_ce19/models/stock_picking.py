# -*- coding: utf-8 -*-
"""
stock_picking.py [v7]

Creates journal entries for BOTH:

1. PURCHASE RECEIPT validation:
   DR  Stock Valuation Account          (110100)
   CR  Stock Input Account / GRNI       (230300)

2. DELIVERY (SALES) validation:
   DR  Stock Interim (Delivered) A/C    (121200)
   CR  Stock Valuation Account          (110100)

Then when Customer Invoice is confirmed (standard Odoo 19):
   DR  600000 Expenses (COGS)
   CR  121200 Stock Interim (Delivered)   ← clears the interim

Reads accounts from custom fields on product.category:
   - property_stock_valuation_account_id  (110100)
   - property_stock_account_input_categ_id (230300)
   - property_stock_account_output_categ_id (121200)
   - property_stock_journal
"""
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ── Receipt journal entries ──────────────────────────────────────────
    receipt_journal_entry_ids = fields.Many2many(
        comodel_name='account.move',
        relation='stock_picking_anglo_saxon_move_rel',
        column1='picking_id',
        column2='move_id',
        string='Receipt Journal Entries',
        copy=False,
        readonly=True,
    )
    receipt_journal_entry_count = fields.Integer(
        compute='_compute_receipt_journal_entry_count',
        string='Receipt Entries',
    )

    # ── Delivery journal entries ─────────────────────────────────────────
    delivery_journal_entry_ids = fields.Many2many(
        comodel_name='account.move',
        relation='stock_picking_delivery_anglo_saxon_rel',
        column1='picking_id',
        column2='move_id',
        string='Delivery Journal Entries',
        copy=False,
        readonly=True,
    )
    delivery_journal_entry_count = fields.Integer(
        compute='_compute_delivery_journal_entry_count',
        string='Delivery Entries',
    )

    @api.depends('receipt_journal_entry_ids')
    def _compute_receipt_journal_entry_count(self):
        for rec in self:
            rec.receipt_journal_entry_count = len(rec.receipt_journal_entry_ids)

    @api.depends('delivery_journal_entry_ids')
    def _compute_delivery_journal_entry_count(self):
        for rec in self:
            rec.delivery_journal_entry_count = len(rec.delivery_journal_entry_ids)

    # ── button_validate override ─────────────────────────────────────────
    def button_validate(self):
        """Create Anglo-Saxon journal entries after receipt or delivery validation."""
        res = super().button_validate()
        for picking in self:
            if picking.state != 'done':
                continue
            try:
                if picking.picking_type_code == 'incoming' \
                        and not picking.receipt_journal_entry_ids:
                    picking._create_receipt_valuation_entry()

                elif picking.picking_type_code == 'outgoing' \
                        and not picking.delivery_journal_entry_ids:
                    picking._create_delivery_valuation_entry()

            except Exception as e:
                _logger.error(
                    "Anglo-Saxon v7: Failed for picking '%s': %s",
                    picking.name, str(e), exc_info=True
                )
        return res

    # ════════════════════════════════════════════════════════════════════
    # PURCHASE RECEIPT
    # DR  Stock Valuation (110100)
    # CR  Stock Input / GRNI (230300)
    # ════════════════════════════════════════════════════════════════════
    def _create_receipt_valuation_entry(self):
        self.ensure_one()
        line_vals = []

        for stock_move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = stock_move.product_id
            categ = product.categ_id

            if not self._is_perpetual(categ):
                continue

            valuation_account = getattr(
                categ, 'property_stock_valuation_account_id', False)
            input_account = getattr(
                categ, 'property_stock_account_input_categ_id', False)

            if not valuation_account or not input_account:
                _logger.warning(
                    "Anglo-Saxon v7 (Receipt): Accounts not set on category '%s'. "
                    "Skipping '%s'.", categ.name, product.name)
                continue

            unit_cost = self._get_unit_cost_receipt(stock_move)
            qty = stock_move.product_uom_qty
            value = unit_cost * qty

            if value <= 0.0:
                continue

            desc = _('%(picking)s - %(product)s') % {
                'picking': self.name,
                'product': product.display_name,
            }

            _logger.info(
                "Anglo-Saxon v7 (Receipt): '%s' product='%s' qty=%s "
                "cost=%s value=%s DR=%s CR=%s",
                self.name, product.name, qty, unit_cost, value,
                valuation_account.name, input_account.name,
            )

            line_vals += [
                {
                    'name': desc,
                    'account_id': valuation_account.id,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
                {
                    'name': desc,
                    'account_id': input_account.id,
                    'debit': 0.0,
                    'credit': value,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
            ]

        if not line_vals:
            return

        journal = self._get_stock_journal()
        if not journal:
            _logger.warning(
                "Anglo-Saxon v7 (Receipt): No stock journal found. "
                "Set Stock Journal on product category.")
            return

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Stock Valuation: %s') % self.name,
            'line_ids': [(0, 0, v) for v in line_vals],
            'company_id': self.company_id.id,
        })
        entry.action_post()
        self.receipt_journal_entry_ids = [(4, entry.id)]
        _logger.info(
            "Anglo-Saxon v7 (Receipt): Created '%s' for picking '%s'.",
            entry.name, self.name)

    # ════════════════════════════════════════════════════════════════════
    # DELIVERY / SALES
    # DR  Stock Interim Delivered (121200)
    # CR  Stock Valuation (110100)
    # ════════════════════════════════════════════════════════════════════
    def _create_delivery_valuation_entry(self):
        self.ensure_one()
        line_vals = []

        for stock_move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = stock_move.product_id
            categ = product.categ_id

            if not self._is_perpetual(categ):
                continue

            valuation_account = getattr(
                categ, 'property_stock_valuation_account_id', False)
            output_account = getattr(
                categ, 'property_stock_account_output_categ_id', False)

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon v7 (Delivery): Stock Valuation Account not set "
                    "on category '%s'. Skipping '%s'.", categ.name, product.name)
                continue

            if not output_account:
                _logger.warning(
                    "Anglo-Saxon v7 (Delivery): Stock Output Account not set "
                    "on category '%s'. Skipping '%s'.", categ.name, product.name)
                continue

            unit_cost = self._get_unit_cost_delivery(stock_move)
            qty = stock_move.product_uom_qty
            value = unit_cost * qty

            if value <= 0.0:
                continue

            desc = _('%(picking)s - %(product)s') % {
                'picking': self.name,
                'product': product.display_name,
            }

            _logger.info(
                "Anglo-Saxon v7 (Delivery): '%s' product='%s' qty=%s "
                "cost=%s value=%s DR=%s CR=%s",
                self.name, product.name, qty, unit_cost, value,
                output_account.name, valuation_account.name,
            )

            line_vals += [
                # DR: Stock Interim Delivered (output account)
                {
                    'name': desc,
                    'account_id': output_account.id,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
                # CR: Stock Valuation (inventory reduces)
                {
                    'name': desc,
                    'account_id': valuation_account.id,
                    'debit': 0.0,
                    'credit': value,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
            ]

        if not line_vals:
            _logger.info(
                "Anglo-Saxon v7 (Delivery): No lines to post for '%s'.", self.name)
            return

        journal = self._get_stock_journal()
        if not journal:
            _logger.warning(
                "Anglo-Saxon v7 (Delivery): No stock journal found.")
            return

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Stock Delivery Valuation: %s') % self.name,
            'line_ids': [(0, 0, v) for v in line_vals],
            'company_id': self.company_id.id,
        })
        entry.action_post()
        self.delivery_journal_entry_ids = [(4, entry.id)]
        _logger.info(
            "Anglo-Saxon v7 (Delivery): Created '%s' for picking '%s'.",
            entry.name, self.name)

    # ════════════════════════════════════════════════════════════════════
    # HELPERS
    # ════════════════════════════════════════════════════════════════════
    # def _is_perpetual(self, categ):
    #     """Return True if category uses perpetual (real-time) valuation."""
    #     val = categ.property_valuation
    #     val_str = str(val).lower()
    #     is_periodic = (
    #         val in ('manual_periodic', 'periodic', 'at_closing')
    #         or ('periodic' in val_str and 'invoic' not in val_str)
    #         or ('closing' in val_str)
    #     )
    #     return not is_periodic and val not in ('', False, None)
    def _is_perpetual(self, categ):
        """Return True if category uses perpetual (real-time) valuation.
        Odoo 19 stores property_valuation as JSONB dict: {"1": "real_time"}
        """
        val = categ.property_valuation
        if not val:
            return False
        # Odoo 19 CE: val is a dict like {"1": "real_time"}
        if isinstance(val, dict):
            val_str = list(val.values())[0] if val else ''
        else:
            val_str = str(val)

        return val_str in ('real_time', 'perpetual', 'perpetual_invoicing')

    def _get_unit_cost_receipt(self, stock_move):
        """Cost for receipt: PO price (FIFO) or standard_price (AVCO/Std)."""
        product = stock_move.product_id
        cost_method = product.categ_id.property_cost_method
        if cost_method == 'fifo':
            po_line = getattr(stock_move, 'purchase_line_id', False)
            if po_line and po_line.price_unit > 0:
                return po_line.price_unit
        return product.standard_price or 0.0

    def _get_unit_cost_delivery(self, stock_move):
        """Cost for delivery: always use current AVCO standard_price."""
        return stock_move.product_id.standard_price or 0.0

    def _get_stock_journal(self):
        """Get stock journal from category or fallback search."""
        for move in self.move_ids.filtered(lambda m: m.state == 'done'):
            journal = getattr(move.product_id.categ_id, 'property_stock_journal', False)
            if journal:
                return journal
        return self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('name', 'ilike', 'Stock'),
            ('company_id', '=', self.company_id.id),
        ], limit=1) or self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    # ── Smart buttons ────────────────────────────────────────────────────
    def action_view_receipt_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.receipt_journal_entry_ids.ids)],
            'context': {'default_move_type': 'entry'},
        }

    def action_view_delivery_journal_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.delivery_journal_entry_ids.ids)],
            'context': {'default_move_type': 'entry'},
        }
