# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
#
#
# class ResPartner(models.Model):
#     _inherit = 'res.partner'
#
#     is_cash_customer = fields.Boolean(
#         string='Is Cash Customer Master',
#         default=False,
#         help='Marks this partner as the master CASH CUSTOMER for POS walk-in sales.'
#     )
#     is_pos_walk_in = fields.Boolean(
#         string='POS Walk-in Contact',
#         default=False,
#         help='This contact was created via POS and is saved under the CASH CUSTOMER master.'
#     )
#
#     @api.model
#     def get_cash_customer_partner(self):
#         """Returns the master CASH CUSTOMER partner, creating it if not found."""
#         partner = self.search([('is_cash_customer', '=', True)], limit=1)
#         if not partner:
#             partner = self.create({
#                 'name': 'CASH CUSTOMER',
#                 'is_cash_customer': True,
#                 'customer_rank': 1,
#                 'company_type': 'person',
#             })
#         return partner
#
#     @api.model
#     def create_pos_walk_in_customer(self, vals):
#         """
#         Creates a new walk-in customer as a child contact under the CASH CUSTOMER master.
#         vals: dict with at minimum 'name', optionally 'phone', 'mobile', 'email'
#         Returns the new partner's id and name.
#         """
#         cash_customer = self.get_cash_customer_partner()
#
#         allowed_fields = ['name', 'phone', 'mobile', 'email', 'street', 'city', 'zip', 'country_id', 'state_id', 'barcode']
#         filtered_vals = {k: v for k, v in vals.items() if k in allowed_fields}
#
#         if not filtered_vals.get('name'):
#             raise UserError(_('Customer name is required.'))
#
#         filtered_vals.update({
#             'parent_id': cash_customer.id,
#             'is_pos_walk_in': True,
#             'customer_rank': 1,
#             'type': 'contact',
#         })
#
#         new_partner = self.create(filtered_vals)
#         return {
#             'id': new_partner.id,
#             'name': new_partner.name,
#             'phone': new_partner.phone or '',
#             'mobile': new_partner.mobile or '',
#             'email': new_partner.email or '',
#             'parent_id': cash_customer.id,
#             'parent_name': cash_customer.name,
#             'is_pos_walk_in': True,
#         }
#
#     @api.model
#     def search_pos_walk_in_customers(self, query, limit=20):
#         """
#         Search walk-in customers under CASH CUSTOMER for POS customer selection.
#         """
#         cash_customer = self.get_cash_customer_partner()
#         domain = [
#             ('parent_id', '=', cash_customer.id),
#             ('is_pos_walk_in', '=', True),
#         ]
#         if query:
#             domain += ['|', '|',
#                 ('name', 'ilike', query),
#                 ('phone', 'ilike', query),
#                 ('mobile', 'ilike', query),
#             ]
#         partners = self.search(domain, limit=limit)
#         return [{
#             'id': p.id,
#             'name': p.name,
#             'phone': p.phone or '',
#             'mobile': p.mobile or '',
#             'email': p.email or '',
#             'parent_id': cash_customer.id,
#             'parent_name': cash_customer.name,
#             'is_pos_walk_in': True,
#         } for p in partners]
#
#     @api.constrains('is_cash_customer')
#     def _check_unique_cash_customer(self):
#         for record in self:
#             if record.is_cash_customer:
#                 existing = self.search([
#                     ('is_cash_customer', '=', True),
#                     ('id', '!=', record.id)
#                 ])
#                 if existing:
#                     raise UserError(_('Only one CASH CUSTOMER master partner is allowed.'))
