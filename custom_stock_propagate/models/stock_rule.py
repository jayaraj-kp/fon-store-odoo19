from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    # -------------------------------------------------------------------------
    # Propagation Fields
    # -------------------------------------------------------------------------
    group_propagation_option = fields.Selection([
        ('none', 'Leave Empty'),
        ('propagate', 'Propagate'),
        ('fixed', 'Fixed'),
    ], string='Propagation of Procurement Group',
        default='propagate',
        help="Choose how the procurement group is propagated on moves created by this rule:\n"
             "- Leave Empty: No procurement group is set.\n"
             "- Propagate: The group is inherited from the origin move.\n"
             "- Fixed: A specific fixed procurement group is always used."
    )

    group_id = fields.Many2one(
        'procurement.group',
        string='Fixed Procurement Group',
        help="Fixed procurement group that will be used on all moves created by this rule "
             "(only used when 'Propagation of Procurement Group' is set to 'Fixed')."
    )

    propagate_carrier = fields.Boolean(
        string='Propagation of Carrier',
        default=False,
        help="If enabled, the carrier set on the originating shipment will be propagated "
             "to the next move created by this rule."
    )

    propagate_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse to Propagate',
        help="Specify a warehouse to propagate on the created move or procurement. "
             "Leave empty to use the default warehouse of the rule."
    )

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------
    @api.onchange('group_propagation_option')
    def _onchange_group_propagation_option(self):
        """Clear group_id when not using fixed propagation."""
        if self.group_propagation_option != 'fixed':
            self.group_id = False

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

        # --- Propagate Procurement Group ---
        if self.group_propagation_option == 'fixed' and self.group_id:
            move_values['group_id'] = self.group_id.id
        elif self.group_propagation_option == 'none':
            move_values['group_id'] = False
        elif self.group_propagation_option == 'propagate':
            group = values.get('group_id')
            if group:
                move_values['group_id'] = group.id if hasattr(group, 'id') else group

        # --- Propagate Carrier ---
        if self.propagate_carrier and values.get('carrier_id'):
            move_values['carrier_id'] = (
                values['carrier_id'].id
                if hasattr(values['carrier_id'], 'id')
                else values['carrier_id']
            )

        return move_values

    # -------------------------------------------------------------------------
    # Override: _run_pull
    # Inject warehouse propagation into procurement values
    # -------------------------------------------------------------------------
    def _run_pull(self, procurements):
        # Inject propagate_warehouse_id into procurement values if set
        updated_procurements = []
        for procurement, rule in procurements:
            if rule.propagate_warehouse_id:
                new_values = dict(procurement.values)
                new_values['warehouse_id'] = rule.propagate_warehouse_id
                from odoo.addons.stock.models.stock_rule import ProcurementGroup
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
