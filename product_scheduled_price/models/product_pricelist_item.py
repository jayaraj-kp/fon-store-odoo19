from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    # Link back to the scheduled price that generated this rule.
    # Deleting the scheduled price deletes the generated rules.
    temp_price_id = fields.Many2one(
        'product.temp.price', string='Scheduled Price',
        ondelete='cascade', index=True, copy=False)
