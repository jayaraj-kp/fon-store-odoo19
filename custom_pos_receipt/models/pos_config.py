from odoo import fields, models
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Ensure the two address columns exist even if the ORM upgrade was skipped."""
    cr = env.cr
    cr.execute("""
        ALTER TABLE pos_config
            ADD COLUMN IF NOT EXISTS pos_address_place   VARCHAR,
            ADD COLUMN IF NOT EXISTS pos_address_city_pin VARCHAR;
    """)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_address_place = fields.Char(
        string='Place / Area',
        help='e.g. MELE CHELARI — printed as the second line of the receipt address.',
    )
    pos_address_city_pin = fields.Char(
        string='City & PIN',
        help='e.g. MALAPPURAM, 673636 — printed as the third line of the receipt address.',
    )

