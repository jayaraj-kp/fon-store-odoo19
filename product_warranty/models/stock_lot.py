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
        help="Date this specific unit (serial number) was most recently "
             "delivered to a customer, whether through a Sales Order or a "
             "POS Order. If this unit was sold, returned, and sold again, "
             "this always reflects the latest sale.",
    )
    return_date = fields.Datetime(
        string="Returned On",
        compute='_compute_warranty_fields',
        help="Date this unit was brought back from the customer, if it is "
             "currently sitting back in stock (i.e. it has not been sold "
             "again since being returned).",
    )
    customer_id = fields.Many2one(
        'res.partner',
        string="Sold To",
        compute='_compute_warranty_fields',
        help="Customer who received this unit on its most recent sale.",
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
            ('returned', 'Returned - Back in Stock'),
        ],
        string="Warranty Status",
        compute='_compute_warranty_fields',
    )

    @api.depends('product_id.warranty_months')
    def _compute_warranty_fields(self):
        """Recomputed every time these fields are read, so the warranty
        status shown to staff is always up to date - no manual refresh
        or scheduled job needed.

        Logic:
        - "Sold On" always reflects the MOST RECENT sale of this unit,
          so if it was sold, returned, and sold again to someone else,
          the warranty resets from that latest sale.
        - "Returned - Back in Stock" is shown only when the unit has a
          sale history AND is currently physically back in our own
          stock (not with any customer) - meaning it was returned and
          has not been resold since.
        """
        StockMoveLine = self.env['stock.move.line']
        StockQuant = self.env['stock.quant']
        for lot in self:
            # Latest time this unit was delivered TO a customer.
            sale_move = StockMoveLine.search(
                [
                    ('lot_id', '=', lot.id),
                    ('state', '=', 'done'),
                    ('location_dest_id.usage', '=', 'customer'),
                ],
                order='date desc',
                limit=1,
            )
            sale_date = sale_move.date if sale_move else False
            lot.sale_date = sale_date
            lot.customer_id = (
                sale_move.picking_id.partner_id.id
                if sale_move and sale_move.picking_id.partner_id
                else False
            )

            # Is this unit physically back in our own stock right now?
            quants = StockQuant.search(
                [
                    ('lot_id', '=', lot.id),
                    ('location_id.usage', '=', 'internal'),
                ]
            )
            qty_in_stock = sum(quants.mapped('quantity'))

            if not sale_date:
                lot.warranty_status = 'not_sold'
                lot.warranty_end_date = False
                lot.return_date = False
                continue

            end_date = False
            if lot.warranty_months:
                end_date = sale_date + relativedelta(months=lot.warranty_months)
            lot.warranty_end_date = end_date

            if qty_in_stock > 0:
                # Sold before, but currently back in stock -> returned,
                # not yet resold. Find when it came back for display.
                return_move = StockMoveLine.search(
                    [
                        ('lot_id', '=', lot.id),
                        ('state', '=', 'done'),
                        ('location_id.usage', '=', 'customer'),
                        ('location_dest_id.usage', '!=', 'customer'),
                    ],
                    order='date desc',
                    limit=1,
                )
                lot.return_date = return_move.date if return_move else False
                lot.warranty_status = 'returned'
            else:
                lot.return_date = False
                if not lot.warranty_months:
                    lot.warranty_status = 'no_warranty'
                else:
                    lot.warranty_status = (
                        'active' if fields.Datetime.now() <= end_date else 'expired'
                    )
