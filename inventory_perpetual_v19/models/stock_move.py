from odoo import models, fields, api, _


class ProductCategory(models.Model):
    _inherit = 'product.category'

    # Define the missing fields manually for Odoo 19 CE
    property_stock_journal = fields.Many2one(
        'account.journal', 'Stock Journal', company_dependent=True,
        help="When doing real-time inventory valuation, this is the Journal in which entries will be posted.")

    property_stock_valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account', company_dependent=True,
        help="Account used to store the current value of the products.")

    property_stock_valuation_variation_account_id = fields.Many2one(
        'account.account', 'Stock Variation Account', company_dependent=True,
        help="Account used to balance the stock valuation entries (replaces Interim accounts).")


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:
            # Check if valuation is set to 'real_time'
            if move.product_id.categ_id.property_valuation == 'real_time':
                move._create_perpetual_accounting_entries()
        return res

    def _create_perpetual_accounting_entries(self):
        self.ensure_one()
        categ = self.product_id.categ_id

        journal = categ.property_stock_journal
        acc_valuation = categ.property_stock_valuation_account_id
        acc_variation = categ.property_stock_valuation_variation_account_id

        if not journal or not acc_valuation or not acc_variation:
            return

        value = self.product_qty * self.price_unit
        if value <= 0:
            return

        if self.location_dest_id.usage == 'internal':  # Incoming
            debit_acc, credit_acc = acc_valuation.id, acc_variation.id
        else:  # Outgoing
            debit_acc, credit_acc = acc_variation.id, acc_valuation.id

        self.env['account.move'].create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': self.reference,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {'name': self.display_name, 'account_id': debit_acc, 'debit': value, 'credit': 0}),
                (0, 0, {'name': self.display_name, 'account_id': credit_acc, 'debit': 0, 'credit': value}),
            ],
        }).action_post()