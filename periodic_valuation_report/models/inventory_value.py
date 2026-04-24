# periodic_valuation_report/models/inventory_value.py
from odoo import models, fields, tools


class StockValuationLine(models.Model):
    """
    SQL view for Odoo 19 CE periodic inventory valuation.

    Odoo 19 CE facts discovered:
    - stock.valuation.layer model does not exist
    - account_move_line has NO stock_move_id column
    - account_move has NO stock_move_id column
    - The only link: account_move.invoice_origin = stock_picking.name

    So: unit_cost and value come from standard_price (always current).
    Journal Entry is linked via invoice_origin = picking name.
    """
    _name = 'periodic.stock.valuation.line'
    _description = 'Periodic Stock Valuation Line'
    _auto = False
    _order = 'date desc'

    date            = fields.Datetime('Date',            readonly=True)
    reference       = fields.Char('Reference',           readonly=True)
    account_move_id = fields.Many2one('account.move',    'Journal Entry', readonly=True)
    product_id      = fields.Many2one('product.product', 'Product',       readonly=True)
    quantity        = fields.Float('Quantity',            readonly=True)
    unit_cost       = fields.Float('Unit Value',          readonly=True, digits='Product Price')
    value           = fields.Float('Total Value',         readonly=True, digits='Product Price')
    company_id      = fields.Many2one('res.company',     'Company',       readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'periodic_stock_valuation_line')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW periodic_stock_valuation_line AS (
                SELECT
                    sml.id                                        AS id,
                    sm.date                                       AS date,
                    COALESCE(sp.name, sm.origin, sm.name)        AS reference,
                    -- Link journal entry via picking name = invoice_origin
                    am.id                                         AS account_move_id,
                    sml.product_id                               AS product_id,
                    -- Positive qty = stock IN, negative = stock OUT
                    CASE
                        WHEN dest_loc.usage = 'internal'
                         AND src_loc.usage  != 'internal'
                        THEN  sml.quantity
                        WHEN src_loc.usage  = 'internal'
                         AND dest_loc.usage != 'internal'
                        THEN -sml.quantity
                        ELSE 0
                    END                                          AS quantity,
                    -- Unit cost from standard_price at product level
                    COALESCE(pt.standard_price, 0)              AS unit_cost,
                    -- Total value = signed quantity × standard_price
                    CASE
                        WHEN dest_loc.usage = 'internal'
                         AND src_loc.usage  != 'internal'
                        THEN  sml.quantity * COALESCE(pt.standard_price, 0)
                        WHEN src_loc.usage  = 'internal'
                         AND dest_loc.usage != 'internal'
                        THEN -sml.quantity * COALESCE(pt.standard_price, 0)
                        ELSE 0
                    END                                          AS value,
                    sm.company_id                               AS company_id
                FROM stock_move_line    sml
                JOIN stock_move         sm
                  ON sm.id        = sml.move_id
                JOIN stock_location     src_loc
                  ON src_loc.id   = sml.location_id
                JOIN stock_location     dest_loc
                  ON dest_loc.id  = sml.location_dest_id
                JOIN product_product    pp
                  ON pp.id        = sml.product_id
                JOIN product_template   pt
                  ON pt.id        = pp.product_tmpl_id
                LEFT JOIN stock_picking sp
                  ON sp.id        = sm.picking_id
                -- Journal entry linked via picking name = invoice_origin
                LEFT JOIN account_move  am
                  ON am.invoice_origin = sp.name
                 AND am.move_type      = 'entry'
                 AND am.state          = 'posted'
                WHERE sm.state = 'done'
                  AND (
                      (dest_loc.usage = 'internal' AND src_loc.usage != 'internal')
                   OR (src_loc.usage  = 'internal' AND dest_loc.usage != 'internal')
                  )
            )
        """)