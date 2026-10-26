from datetime import timedelta

from odoo import fields, models


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    # Link back to the scheduled price that generated this rule.
    # Rules are never deleted automatically (POS keeps a local copy of
    # deleted rules); they are expired instead.
    temp_price_id = fields.Many2one(
        'product.temp.price', string='Scheduled Price',
        ondelete='set null', index=True, copy=False)

    def _expire_scheduled(self):
        """Make the rule inactive without deleting it."""
        past = fields.Datetime.now() - timedelta(days=1)
        for item in self:
            item.write({
                'date_start': past,
                'date_end': past,
                'temp_price_id': False,
            })
