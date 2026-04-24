# periodic_valuation_report/models/inventory_value.py
from odoo import models, fields, tools


class StockValuationLine(models.Model):
    """
    SQL view for Odoo 19 CE periodic inventory valuation.

    Confirmed stock_move columns used:
    - date, reference, origin, state, picking_id, company_id
    - price_unit  → unit cost at time of move
    - value       → total monetary value of the move
    - account_move_id → direct FK to account.move (journal entry)!
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
                    sm.id                                         AS id,
                    sm.date                                       AS date,
                    COALESCE(sp.name, sm.reference, sm.origin)   AS reference,
                    sm.account_move_id                            AS account_move_id,
                    sm.product_id                                 AS product_id,
                    -- Positive = IN to internal, Negative = OUT from internal
                    CASE
                        WHEN sm.is_in  THEN  sm.quantity
                        WHEN sm.is_out THEN -sm.quantity
                        ELSE 0
                    END                                           AS quantity,
                    sm.price_unit                                 AS unit_cost,
                    -- value on stock_move is always positive; sign it by direction
                    CASE
                        WHEN sm.is_in  THEN  ABS(sm.value)
                        WHEN sm.is_out THEN -ABS(sm.value)
                        ELSE 0
                    END                                           AS value,
                    sm.company_id                                 AS company_id
                FROM stock_move         sm
                LEFT JOIN stock_picking sp ON sp.id = sm.picking_id
                WHERE sm.state = 'done'
                  AND (sm.is_in OR sm.is_out)
            )
        """)