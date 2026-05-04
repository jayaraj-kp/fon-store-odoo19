# -*- coding: utf-8 -*-
"""
stock_picking.py

Creates Anglo-Saxon journal entries at:
  1. PURCHASE RECEIPT validation:
       DR  110100  Stock Valuation
       CR  230300  Stock Interim (Received) / GRNI

  2. DELIVERY (SALES) validation:
       DR  121200  Stock Interim (Delivered)
       CR  110100  Stock Valuation

Then when Customer Invoice is confirmed (standard Odoo 19 + account_move.py fix):
       DR  600000  Expenses (COGS)
       CR  121200  Stock Interim (Delivered)   ← clears the interim

All accounts are read from stock_account_category_fix fields on product.category.

Notes on Odoo 19 CE:
  - property_valuation is stored as JSONB: {"1": "real_time"} — handled in _is_perpetual().
  - sudo() is required in button_validate guard and entry creation to handle
    warehouse/POS users who lack accounting access.
  - _action_done fallback handles non-POS programmatic picking validation
    (scheduler, automated actions). POS pickings are handled by pos_stock_picking.py.
"""
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

PERPETUAL_VALUES = frozenset({'real_time', 'perpetual', 'perpetual_invoicing'})


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ── Receipt journal entries ──────────────────────────────────────────────
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

    # ── Delivery journal entries ─────────────────────────────────────────────
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
            # sudo() — warehouse/POS users lack accounting access
            rec.receipt_journal_entry_count = len(rec.sudo().receipt_journal_entry_ids)

    @api.depends('delivery_journal_entry_ids')
    def _compute_delivery_journal_entry_count(self):
        for rec in self:
            rec.delivery_journal_entry_count = len(rec.sudo().delivery_journal_entry_ids)

    # ── button_validate ──────────────────────────────────────────────────────
    def button_validate(self):
        """
        Create Anglo-Saxon journal entries after receipt or delivery validation.
        Called when a user manually validates from the UI.
        """
        res = super().button_validate()
        for picking in self:
            if picking.state != 'done':
                continue
            try:
                # sudo() for the guard — non-admin users cannot read account.move
                # without it, the guard always returns empty and creates duplicates.
                picking_sudo = picking.sudo()

                if picking.picking_type_code == 'incoming' \
                        and not picking_sudo.receipt_journal_entry_ids:
                    picking._create_receipt_valuation_entry()

                elif picking.picking_type_code == 'outgoing' \
                        and not picking_sudo.delivery_journal_entry_ids:
                    picking._create_delivery_valuation_entry()

            except Exception:
                _logger.error(
                    "Anglo-Saxon: Failed for picking '%s'",
                    picking.name, exc_info=True,
                )
        return res

    # ── PURCHASE RECEIPT ─────────────────────────────────────────────────────
    # DR  Stock Valuation   (110100)
    # CR  Stock Input/GRNI  (230300)
    # ────────────────────────────────────────────────────────────────────────
    def _create_receipt_valuation_entry(self):
        self.ensure_one()
        line_vals = []

        for stock_move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = stock_move.product_id
            categ = product.categ_id

            if not self._is_perpetual(categ):
                continue

            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            input_account = getattr(categ, 'property_stock_account_input_categ_id', False)

            if not valuation_account or not input_account:
                _logger.warning(
                    "Anglo-Saxon (Receipt): Accounts missing on category '%s' "
                    "— skipping product '%s'. "
                    "Set Stock Valuation Account and Stock Input Account on the category.",
                    categ.name, product.name,
                )
                continue

            unit_cost = self._get_unit_cost_receipt(stock_move)
            qty = stock_move.product_uom_qty
            value = round(unit_cost * qty, 2)

            if value <= 0.0:
                _logger.debug(
                    "Anglo-Saxon (Receipt): zero value for '%s' — skipping.",
                    product.name,
                )
                continue

            desc = _('%(picking)s — %(product)s') % {
                'picking': self.name,
                'product': product.display_name,
            }

            _logger.info(
                "Anglo-Saxon (Receipt): picking='%s' product='%s' qty=%s "
                "unit_cost=%s value=%s  DR=%s  CR=%s",
                self.name, product.name, qty, unit_cost, value,
                valuation_account.code, input_account.code,
            )

            line_vals += [
                {   # DR Stock Valuation
                    'name': desc,
                    'account_id': valuation_account.id,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
                {   # CR Stock Interim Received (GRNI)
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
            _logger.info("Anglo-Saxon (Receipt): no lines to post for '%s'.", self.name)
            return

        journal = self._get_stock_journal()
        if not journal:
            _logger.warning(
                "Anglo-Saxon (Receipt): No stock journal found for picking '%s'. "
                "Set Stock Journal on the product category.",
                self.name,
            )
            return

        entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Stock Valuation: %s') % self.name,
            'line_ids': [(0, 0, v) for v in line_vals],
            'company_id': self.company_id.id,
        })
        entry.sudo().action_post()
        self.sudo().receipt_journal_entry_ids = [(4, entry.id)]
        _logger.info(
            "Anglo-Saxon (Receipt): Created entry '%s' for picking '%s'.",
            entry.name, self.name,
        )

    # ── DELIVERY / SALES ─────────────────────────────────────────────────────
    # DR  Stock Interim Delivered  (121200)
    # CR  Stock Valuation          (110100)
    # ────────────────────────────────────────────────────────────────────────
    def _create_delivery_valuation_entry(self):
        self.ensure_one()
        line_vals = []

        for stock_move in self.move_ids.filtered(lambda m: m.state == 'done'):
            product = stock_move.product_id
            categ = product.categ_id

            if not self._is_perpetual(categ):
                continue

            valuation_account = getattr(categ, 'property_stock_valuation_account_id', False)
            output_account = getattr(categ, 'property_stock_account_output_categ_id', False)

            if not valuation_account:
                _logger.warning(
                    "Anglo-Saxon (Delivery): Stock Valuation Account missing on "
                    "category '%s' — skipping '%s'.", categ.name, product.name,
                )
                continue

            if not output_account:
                _logger.warning(
                    "Anglo-Saxon (Delivery): Stock Output Account missing on "
                    "category '%s' — skipping '%s'.", categ.name, product.name,
                )
                continue

            unit_cost = self._get_unit_cost_delivery(stock_move)
            qty = stock_move.product_uom_qty
            value = round(unit_cost * qty, 2)

            if value <= 0.0:
                _logger.debug(
                    "Anglo-Saxon (Delivery): zero value for '%s' — skipping.",
                    product.name,
                )
                continue

            desc = _('%(picking)s — %(product)s') % {
                'picking': self.name,
                'product': product.display_name,
            }

            _logger.info(
                "Anglo-Saxon (Delivery): picking='%s' product='%s' qty=%s "
                "unit_cost=%s value=%s  DR=%s  CR=%s",
                self.name, product.name, qty, unit_cost, value,
                output_account.code, valuation_account.code,
            )

            line_vals += [
                {   # DR Stock Interim Delivered
                    'name': desc,
                    'account_id': output_account.id,
                    'debit': value,
                    'credit': 0.0,
                    'product_id': product.id,
                    'product_uom_id': stock_move.product_uom.id,
                    'quantity': qty,
                },
                {   # CR Stock Valuation (inventory decreases)
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
            _logger.info("Anglo-Saxon (Delivery): no lines to post for '%s'.", self.name)
            return

        journal = self._get_stock_journal()
        if not journal:
            _logger.warning(
                "Anglo-Saxon (Delivery): No stock journal found for picking '%s'.",
                self.name,
            )
            return

        entry = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Stock Delivery Valuation: %s') % self.name,
            'line_ids': [(0, 0, v) for v in line_vals],
            'company_id': self.company_id.id,
        })
        entry.sudo().action_post()
        self.sudo().delivery_journal_entry_ids = [(4, entry.id)]
        _logger.info(
            "Anglo-Saxon (Delivery): Created entry '%s' for picking '%s'.",
            entry.name, self.name,
        )

    # ── HELPERS ──────────────────────────────────────────────────────────────

    def _is_perpetual(self, categ):
        """
        Return True if category uses perpetual (real-time) valuation.

        Odoo 19 CE stores company_dependent selection fields as JSONB:
            {"1": "real_time"}   ← company id 1 → value
        This method handles both the dict form and plain string form.
        """
        val = categ.property_valuation
        if not val:
            return False
        if isinstance(val, dict):
            val_str = next(iter(val.values()), '') if val else ''
        else:
            val_str = str(val)
        return val_str in PERPETUAL_VALUES

    def _get_unit_cost_receipt(self, stock_move):
        """
        Cost to use for a purchase receipt line.
        - FIFO: use the confirmed PO line price (price_unit after tax mapping).
        - AVCO / Standard: use product's current standard_price (AVCO updates
          standard_price on bill validation in At Invoicing mode).
        """
        product = stock_move.product_id
        cost_method = product.categ_id.property_cost_method
        if cost_method == 'fifo':
            po_line = getattr(stock_move, 'purchase_line_id', False)
            if po_line and po_line.price_unit > 0:
                return po_line.price_unit
        return product.standard_price or 0.0

    def _get_unit_cost_delivery(self, stock_move):
        """
        Cost to use for a delivery/sales line.
        Always uses the product's current standard_price (AVCO value).
        For FIFO this will be the oldest lot cost — standard_price holds it.
        """
        return stock_move.product_id.standard_price or 0.0

    def _get_stock_journal(self):
        """
        Resolve stock journal in order of preference:
        1. property_stock_journal from the product category.
        2. A general journal with 'Stock' in its name for this company.
        3. Any general journal for this company (last resort).
        """
        for move in self.move_ids.filtered(lambda m: m.state == 'done'):
            journal = getattr(move.product_id.categ_id, 'property_stock_journal', False)
            if journal:
                return journal

        Journal = self.env['account.journal']
        return (
            Journal.search([
                ('type', '=', 'general'),
                ('name', 'ilike', 'Stock'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            or Journal.search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        )

    # ── Smart buttons ────────────────────────────────────────────────────────

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
