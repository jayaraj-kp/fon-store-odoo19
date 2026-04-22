# from odoo import fields, models
#
# class ProductCategory(models.Model):
#     _inherit = 'product.category'
#
#     property_stock_valuation_account_id = fields.Many2one(
#         comodel_name='account.account',
#         string='Stock Valuation Account',
#         company_dependent=True,
#     )
#     property_stock_journal = fields.Many2one(
#         comodel_name='account.journal',
#         string='Stock Journal',
#         company_dependent=True,
#     )
#     property_stock_account_input_categ_id = fields.Many2one(
#         comodel_name='account.account',
#         string='Stock Input Account',
#         company_dependent=True,
#     )
#     property_stock_account_output_categ_id = fields.Many2one(
#         comodel_name='account.account',
#         string='Stock Output Account',
#         company_dependent=True,
#     )
from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_valuation_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Valuation Account',
        company_dependent=True,
    )
    property_stock_journal = fields.Many2one(
        comodel_name='account.journal',
        string='Stock Journal',
        company_dependent=True,
    )
    property_stock_account_input_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Input Account',
        company_dependent=True,
    )
    property_stock_account_output_categ_id = fields.Many2one(
        comodel_name='account.account',
        string='Stock Output Account',
        company_dependent=True,
    )

    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Helper to safely resolve an XML ID to a record
        def get_account(xml_id):
            try:
                return self.env.ref(xml_id).id
            except Exception:
                return False

        # Stock Interim (Received) — used as the Stock Input Account default
        if 'property_stock_account_input_categ_id' in fields_list:
            account_id = get_account('stock_account.stock_account_interim_received')
            if account_id:
                res['property_stock_account_input_categ_id'] = account_id

        # Stock Interim (Delivered) — used as the Stock Output Account default
        if 'property_stock_account_output_categ_id' in fields_list:
            account_id = get_account('stock_account.stock_account_interim_delivered')
            if account_id:
                res['property_stock_account_output_categ_id'] = account_id

        return res