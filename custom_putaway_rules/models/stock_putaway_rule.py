# models/stock_putaway_rule.py

from odoo import models, fields, api


class StockPutawayRule(models.Model):
    """
    Extended Stock Putaway Rule Model

    PURPOSE:
    Override the location_in_id field domain to show all locations
    instead of just parent locations (those with child_ids).

    ORIGINAL BEHAVIOR:
    - location_in_id only showed locations with child_ids
    - Original domain: [('company_id', 'in', [company_id] + [False])] +
                      ([('child_ids', '!=', False)]) or [('company_id', '=', False)]

    NEW BEHAVIOR:
    - Shows all company locations (parent and sub-locations)
    - New domain: [('company_id', 'in', [company_id, False])]

    BENEFIT:
    - Users can create putaway rules for sub-locations directly
    - More flexible warehouse location management
    - Backward compatible with existing rules
    """

    _inherit = 'stock.putaway.rule'

    # Override the location_in_id field with new domain
    location_in_id = fields.Many2one(
        comodel_name='stock.location',
        string='When product arrives in',
        required=True,
        domain="[('company_id', 'in', [company_id, False])]",
        help="The source location for this putaway rule. Shows all warehouse locations including sub-locations."
    )