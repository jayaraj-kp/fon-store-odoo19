from odoo import models, fields, api, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            # Check if valuation is set to 'real_time' (Automated)
            if move.product_id.categ_id.property_valuation == 'real_time':
                move._create_perpetual_accounting_entries()
        return res

    def _create_perpetual_accounting_entries(self):
        self.ensure_one()
        categ = self.product_id.categ_id

        # Odoo 19 Field Names
        journal = categ.property_stock_journal
        acc_valuation = categ.property_stock_valuation_account_id
        acc_variation = categ.property_stock_valuation_variation_account_id

        if not journal or not acc_valuation or not acc_variation:
            return

        # Calculate value (Standard Odoo 19 logic)
        quantity = self.product_qty
        price = self.price_unit
        value = quantity * price

        if value <= 0:
            return

        # Determine direction
        if self.location_dest_id.usage == 'internal':  # Incoming Move
            debit_acc = acc_valuation.id
            credit_acc = acc_variation.id
        else:  # Outgoing Move
            debit_acc = acc_variation.id
            credit_acc = acc_valuation.id

        self.env['account.move'].create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': self.reference,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                    'name': self.display_name,
                    'account_id': debit_acc,
                    'debit': value,
                    'credit': 0,
                }),
                (0, 0, {
                    'name': self.display_name,
                    'account_id': credit_acc,
                    'debit': 0,
                    'credit': value,
                }),
            ],
        }).action_post()