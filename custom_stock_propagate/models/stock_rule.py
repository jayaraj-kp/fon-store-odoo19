from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # -------------------------------------------------------------------------
    # Propagation Fields
    # Note: procurement.group was removed in Odoo 19.
    # We keep propagate_carrier and propagate_warehouse_id which are still valid.
    # -------------------------------------------------------------------------

    propagate_carrier = fields.Boolean(
        string='Propagate Carrier',
        default=False,
        help="If enabled, the carrier set on the originating shipment will be "
             "propagated to the next move created by this rule."
    )

    propagate_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse to Propagate',
        help="Specify a warehouse to propagate on the created move or procurement. "
             "Leave empty to use the default warehouse of the rule."
    )

    # -------------------------------------------------------------------------
    # Override: _get_stock_move_values
    # Inject propagation values into stock moves created by this rule
    # -------------------------------------------------------------------------
    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_dest_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(
            product_id, product_qty, product_uom,
            location_dest_id, name, origin, company_id, values
        )

        # --- Propagate Carrier ---
        if self.propagate_carrier and values.get('carrier_id'):
            carrier = values['carrier_id']
            move_values['carrier_id'] = carrier.id if hasattr(carrier, 'id') else carrier

        return move_values

    # -------------------------------------------------------------------------
    # Override: _run_pull
    # Inject warehouse propagation into procurement values
    # -------------------------------------------------------------------------
    def _run_pull(self, procurements):
        updated_procurements = []
        for procurement, rule in procurements:
            if rule.propagate_warehouse_id:
                new_values = dict(procurement.values)
                new_values['warehouse_id'] = rule.propagate_warehouse_id
                updated_procurements.append(
                    procurement.__class__(
                        procurement.product_id,
                        procurement.product_qty,
                        procurement.product_uom,
                        procurement.location_id,
                        procurement.name,
                        procurement.origin,
                        procurement.company_id,
                        new_values,
                    )
                )
            else:
                updated_procurements.append(procurement)
        return super()._run_pull(updated_procurements)
