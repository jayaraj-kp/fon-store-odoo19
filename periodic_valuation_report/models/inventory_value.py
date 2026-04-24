# periodic_valuation_report/models/inventory_value.py
from odoo import models, fields, tools


class StockValuationLine(models.Model):
    """
    SQL view model that replicates stock.valuation.layer behaviour for Odoo 19 CE.
    Pulls data from stock_move + account_move_line to show:
      Date | Reference | Journal Entry | Product | Quantity | Unit Value | Total Value
    """
    _name = 'periodic.stock.valuation.line'
    _description = 'Periodic Stock Valuation Line'
    _auto = False          # tell Odoo: don't create a table, we provide the SQL view
    _order = 'date desc'

    date          = fields.Datetime('Date',          readonly=True)
    reference     = fields.Char('Reference',         readonly=True)
    account_move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    product_id    = fields.Many2one('product.product', 'Product',      readonly=True)
    quantity      = fields.Float('Quantity',         readonly=True)
    unit_cost     = fields.Float('Unit Value',       readonly=True, digits='Product Price')
    value         = fields.Float('Total Value',      readonly=True, digits='Product Price')
    company_id    = fields.Many2one('res.company',   'Company',        readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'periodic_stock_valuation_line')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW periodic_stock_valuation_line AS (
                SELECT
                    sml.id                          AS id,
                    sm.date                         AS date,
                    COALESCE(sp.name, sm.name, sm.reference)  AS reference,
                    aml.move_id                     AS account_move_id,
                    sml.product_id                  AS product_id,
                    -- positive qty = stock IN (dest = internal), negative = OUT
                    CASE
                        WHEN dest_loc.usage = 'internal'
                         AND src_loc.usage  != 'internal' THEN  sml.quantity
                        WHEN src_loc.usage  = 'internal'
                         AND dest_loc.usage != 'internal' THEN -sml.quantity
                        ELSE 0
                    END                             AS quantity,
                    CASE
                        WHEN sml.quantity != 0
                        THEN ABS(aml.balance) / ABS(
                            NULLIF(
                                CASE
                                    WHEN dest_loc.usage = 'internal'
                                     AND src_loc.usage  != 'internal' THEN  sml.quantity
                                    WHEN src_loc.usage  = 'internal'
                                     AND dest_loc.usage != 'internal' THEN -sml.quantity
                                    ELSE sml.quantity
                                END, 0)
                            )
                        ELSE 0
                    END                             AS unit_cost,
                    aml.balance                     AS value,
                    sm.company_id                   AS company_id
                FROM stock_move_line sml
                JOIN stock_move         sm       ON sm.id       = sml.move_id
                JOIN stock_location     src_loc  ON src_loc.id  = sml.location_id
                JOIN stock_location     dest_loc ON dest_loc.id = sml.location_dest_id
                LEFT JOIN stock_picking sp       ON sp.id       = sm.picking_id
                -- join to account move lines that reference this stock move
                LEFT JOIN account_move_line aml  ON aml.stock_move_id = sm.id
                                                 AND aml.display_type  = 'product'
                WHERE sm.state = 'done'
                  AND (
                      -- incoming: dest is internal
                      (dest_loc.usage = 'internal' AND src_loc.usage != 'internal')
                      OR
                      -- outgoing: src is internal
                      (src_loc.usage = 'internal' AND dest_loc.usage != 'internal')
                  )
            )
        """)