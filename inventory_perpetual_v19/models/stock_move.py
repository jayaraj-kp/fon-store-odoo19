from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        # 1. Execute standard stock move logic
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)

        for move in self:
            # 2. Only generate entry if it's an internal-to-external (or vice versa) move
            # and the product category is set to 'automated'
            if move.product_id.valuation == 'real_time':
                move._create_account_move_entry()
        return res

    def _create_account_move_entry(self):
        self.ensure_one()
        journal_id = self.product_id.categ_id.property_stock_journal.id
        acc_valuation = self.product_id.categ_id.property_stock_valuation_account_id.id
        # In Odoo 19, property_stock_account_input_categ_id acts as the variation account
        acc_variation = self.product_id.categ_id.property_stock_account_input_categ_id.id

        if not journal_id or not acc_valuation or not acc_variation:
            return  # Skip if accounts are not configured

        value = self.product_qty * self.price_unit  # Adjust based on your costing method

        if value == 0:
            return

        # Determine Debit vs Credit based on direction
        if self.location_dest_id.usage == 'internal':  # Incoming
            debit_acc = acc_valuation
            credit_acc = acc_variation
        else:  # Outgoing
            debit_acc = acc_variation
            credit_acc = acc_valuation

        move_vals = {
            'journal_id': journal_id,
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
        }
        self.env['account.move'].create(move_vals).action_post()