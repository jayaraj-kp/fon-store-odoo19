# from odoo import api, fields, models
#
#
# class StockRule(models.Model):
#     _inherit = 'stock.rule'
#
#     group_propagation_option = fields.Selection([
#         ('none', 'Leave Empty'),
#         ('propagate', 'Propagate'),
#         ('fixed', 'Fixed'),
#     ], string='Propagation of Procurement Group',
#         default='propagate',
#         help="Choose how the procurement group is propagated on moves created by this rule:\n"
#              "- Leave Empty: No procurement group is set.\n"
#              "- Propagate: The group is inherited from the origin move.\n"
#              "- Fixed: A specific fixed procurement group is always used."
#     )
#
#     propagate_carrier = fields.Boolean(
#         string='Propagate Carrier',
#         default=False,
#         help="If enabled, the carrier set on the originating shipment will be "
#              "propagated to the next move created by this rule."
#     )
#
#     propagate_warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse to Propagate',
#         help="Specify a warehouse to propagate on the created move or procurement. "
#              "Leave empty to use the default warehouse of the rule."
#     )
#
#     def _get_stock_move_values(self, product_id, product_qty, product_uom,
#                                location_dest_id, name, origin, company_id, values):
#         move_values = super()._get_stock_move_values(
#             product_id, product_qty, product_uom,
#             location_dest_id, name, origin, company_id, values
#         )
#
#         # --- Propagate Carrier ---
#         if self.propagate_carrier and values.get('carrier_id'):
#             carrier = values['carrier_id']
#             move_values['carrier_id'] = carrier.id if hasattr(carrier, 'id') else carrier
#
#         return move_values
#
#     def _run_pull(self, procurements):
#         updated_procurements = []
#         for procurement, rule in procurements:
#             if rule.propagate_warehouse_id:
#                 new_values = dict(procurement.values)
#                 new_values['warehouse_id'] = rule.propagate_warehouse_id
#                 updated_procurements.append(
#                     procurement.__class__(
#                         procurement.product_id,
#                         procurement.product_qty,
#                         procurement.product_uom,
#                         procurement.location_id,
#                         procurement.name,
#                         procurement.origin,
#                         procurement.company_id,
#                         new_values,
#                     )
#                 )
#             else:
#                 updated_procurements.append(procurement)
#         return super()._run_pull(updated_procurements)

#get error when the sale quotation confirm time so comment the code and use the updated code below
from odoo import api, fields, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

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

    def _run_pull(self, procurements):
        updated_procurements = []
        for procurement, rule in procurements:
            if rule.propagate_warehouse_id:
                new_values = dict(procurement.values)
                new_values['warehouse_id'] = rule.propagate_warehouse_id
                updated_procurement = procurement.__class__(
                    procurement.product_id,
                    procurement.product_qty,
                    procurement.product_uom,
                    procurement.location_id,
                    procurement.name,
                    procurement.origin,
                    procurement.company_id,
                    new_values,
                )
                updated_procurements.append((updated_procurement, rule))  # ✅ 2-tuple
            else:
                updated_procurements.append((procurement, rule))  # ✅ 2-tuple
        return super()._run_pull(updated_procurements)