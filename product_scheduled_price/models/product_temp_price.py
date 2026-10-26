from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductTempPrice(models.Model):
    _name = 'product.temp.price'
    _description = 'Product Scheduled Price'
    _order = 'date_start desc, id desc'

    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True, ondelete='cascade', index=True)
    price = fields.Float(string='Scheduled Price', required=True, digits='Product Price')
    # Datetime fields: shown in the user's timezone, stored in UTC by Odoo
    date_start = fields.Datetime(string='Start', required=True, default=fields.Datetime.now)
    date_end = fields.Datetime(string='End', required=True)
    pricelist_ids = fields.Many2many(
        'product.pricelist', string='Pricelists',
        help="The scheduled price is applied on these pricelists. "
             "For POS, they must also be available in the POS configuration.")
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    item_ids = fields.One2many(
        'product.pricelist.item', 'temp_price_id', string='Generated Pricelist Rules')

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_end <= rec.date_start:
                raise ValidationError(self.env._("End must be after Start."))

    @api.constrains('pricelist_ids')
    def _check_pricelists(self):
        for rec in self:
            if not rec.pricelist_ids:
                raise ValidationError(self.env._("Please select at least one pricelist."))

    # ------------------------------------------------------------------
    # Sync with native pricelist rules (used by both Sales and POS)
    # ------------------------------------------------------------------
    def _sync_items(self):
        """Create/update one pricelist rule per selected pricelist.

        Existing rules are updated in place (never deleted), so the POS,
        which caches rules locally, always receives the change.
        """
        Item = self.env['product.pricelist.item'].sudo()
        for rec in self:
            company = rec.company_id or self.env.company
            existing = {
                item.pricelist_id.id: item for item in rec.item_ids.sudo()
            }
            for pricelist in rec.pricelist_ids:
                price = rec.price
                if pricelist.currency_id and pricelist.currency_id != company.currency_id:
                    price = company.currency_id._convert(
                        price, pricelist.currency_id, company, rec.date_start.date())
                vals = {
                    'pricelist_id': pricelist.id,
                    'applied_on': '1_product',
                    'product_tmpl_id': rec.product_tmpl_id.id,
                    'compute_price': 'fixed',
                    'fixed_price': price,
                    'min_quantity': 0,
                    'date_start': rec.date_start,
                    'date_end': rec.date_end,
                    'temp_price_id': rec.id,
                }
                item = existing.pop(pricelist.id, None)
                if item:
                    item.write(vals)
                else:
                    Item.create(vals)
            # pricelists that were removed from the row: expire, do not delete
            for item in existing.values():
                item._expire_scheduled()

    def unlink(self):
        # expire the generated rules instead of deleting them
        self.item_ids.sudo()._expire_scheduled()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_items()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {'price', 'date_start', 'date_end', 'pricelist_ids',
                'product_tmpl_id', 'company_id'} & set(vals):
            self._sync_items()
        return res
