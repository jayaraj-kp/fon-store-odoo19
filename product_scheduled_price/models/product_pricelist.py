from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _get_product_price(self, product, quantity, currency=None, uom=None,
                           date=False, **kwargs):
        """Return the scheduled price if one is active on the pricing date,
        otherwise fall back to the standard pricelist computation."""
        price = super()._get_product_price(
            product, quantity, currency=currency, uom=uom, date=date, **kwargs)

        check_date = fields.Date.to_date(date) if date else fields.Date.context_today(self)
        temp = self.env['product.temp.price'].sudo().search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            ('date_start', '<=', check_date),
            ('date_end', '>=', check_date),
        ], order='date_start desc, id desc', limit=1)
        if not temp:
            return price

        new_price = temp.price
        # unit of measure conversion
        if uom and uom != product.uom_id:
            new_price = product.uom_id._compute_price(new_price, uom)
        # currency conversion (scheduled price is stored in company currency)
        currency = currency or self.currency_id
        company = temp.company_id or self.env.company
        if currency and currency != company.currency_id:
            new_price = company.currency_id._convert(
                new_price, currency, company, check_date)
        return new_price
