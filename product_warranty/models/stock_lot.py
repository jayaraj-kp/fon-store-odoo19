from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    warranty_months = fields.Integer(
        related='product_id.warranty_months',
        string="Warranty (Months)",
        readonly=True,
    )
    sale_date = fields.Datetime(
        string="Sold On",
        compute='_compute_warranty_fields',
        help="Date this specific unit (serial number) was delivered to a "
             "customer, whether through a Sales Order or a POS Order.",
    )
    warranty_end_date = fields.Datetime(
        string="Warranty End Date",
        compute='_compute_warranty_fields',
    )
    warranty_status = fields.Selection(
        [
            ('not_sold', 'Not Sold Yet'),
            ('no_warranty', 'No Warranty Configured'),
            ('active', 'Under Warranty'),
            ('expired', 'Warranty Expired'),
        ],
        string="Warranty Status",
        compute='_compute_warranty_fields',
    )

    @api.depends('product_id.warranty_months')
    def _compute_warranty_fields(self):
        """Recomputed every time these fields are read, so the warranty
        status shown to staff is always up to date - no manual refresh
        or scheduled job needed."""
        StockMoveLine = self.env['stock.move.line']
        for lot in self:
            move_line = StockMoveLine.search(
                [
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'customer'),
                ],
                order='date desc',
                limit=1,
            )
            sale_date = move_line.date if move_line else False
            lot.sale_date = sale_date

            if not sale_date:
                lot.warranty_status = 'not_sold'
                lot.warranty_end_date = False
            elif not lot.warranty_months:
                lot.warranty_status = 'no_warranty'
                lot.warranty_end_date = False
            else:
                end_date = sale_date + relativedelta(months=lot.warranty_months)
                lot.warranty_end_date = end_date
                lot.warranty_status = (
                    'active' if fields.Datetime.now() <= end_date else 'expired'
                )
