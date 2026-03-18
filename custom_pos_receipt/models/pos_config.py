from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # ── Receipt Address Block ──────────────────────────────────────────────
    # These fields appear on the POS Configuration form (new "Receipt Address"
    # tab) and are printed on the receipt header instead of / before falling
    # back to the warehouse or company address.

    pos_address_place = fields.Char(
        string='Place / Area',
        help='e.g. MELE CHELARI — printed as the second line of the receipt address.',
    )
    pos_address_city_pin = fields.Char(
        string='City & PIN',
        help='e.g. MALAPPURAM, 673636 — printed as the third line of the receipt address.',
    )

