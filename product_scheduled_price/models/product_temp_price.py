from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTempPrice(models.Model):
    _name = 'product.temp.price'
    _description = 'Product Scheduled Price'
    _order = 'date_start desc, id desc'

    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True, ondelete='cascade', index=True)
    price = fields.Float(string='Scheduled Price', required=True, digits='Product Price')
    date_start = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_end = fields.Date(string='End Date', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end < rec.date_start:
                raise ValidationError(self.env._("End date cannot be before start date."))
