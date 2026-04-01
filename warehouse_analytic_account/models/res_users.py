# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # property_warehouse_id already exists in stock module as a many2one to
    # stock.warehouse.  We just add a computed helper that returns the linked
    # analytic account (if any) so other models can read it easily.

    warehouse_analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Warehouse Analytic Account',
        compute='_compute_warehouse_analytic_account_id',
        store=False,
    )

    @api.depends('property_warehouse_id', 'property_warehouse_id.analytic_account_id')
    def _compute_warehouse_analytic_account_id(self):
        for user in self:
            wh = user.property_warehouse_id
            user.warehouse_analytic_account_id = (
                wh.analytic_account_id if wh else False
            )
