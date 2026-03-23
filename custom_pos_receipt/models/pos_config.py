# from odoo import fields, models
# from odoo import api, SUPERUSER_ID
#
#
# def post_init_hook(env):
#     """Ensure the two address columns exist even if the ORM upgrade was skipped."""
#     cr = env.cr
#     cr.execute("""
#         ALTER TABLE pos_config
#             ADD COLUMN IF NOT EXISTS pos_address_place   VARCHAR,
#             ADD COLUMN IF NOT EXISTS pos_address_city_pin VARCHAR;
#     """)
#
#
# class PosConfig(models.Model):
#     _inherit = 'pos.config'
#
#     pos_address_place = fields.Char(
#         string='Place / Area',
#         help='e.g. MELE CHELARI — printed as the second line of the receipt address.',
#     )
#     pos_address_city_pin = fields.Char(
#         string='City & PIN',
#         help='e.g. MALAPPURAM, 673636 — printed as the third line of the receipt address.',
#     )
#


from odoo import fields, models
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    """Ensure the address columns exist even if the ORM upgrade was skipped."""
    cr = env.cr
    cr.execute("""
        ALTER TABLE pos_config
            ADD COLUMN IF NOT EXISTS pos_address_street   VARCHAR,
            ADD COLUMN IF NOT EXISTS pos_address_place    VARCHAR,
            ADD COLUMN IF NOT EXISTS pos_address_city_pin VARCHAR,
            ADD COLUMN IF NOT EXISTS pos_address_phone    VARCHAR;
    """)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_address_street = fields.Char(
        string='Street / Address',
        help='e.g. 123, Main Road, Near Bus Stand — printed as the first address line on the receipt.',
    )
    pos_address_place = fields.Char(
        string='Place / Area',
        help='e.g. MELE CHELARI — printed as the second line of the receipt address.',
    )
    pos_address_city_pin = fields.Char(
        string='City & PIN',
        help='e.g. MALAPPURAM, 673636 — printed as the third line of the receipt address.',
    )
    pos_address_phone = fields.Char(
        string='Phone',
        help='e.g. +91 90000 00000 — printed on the receipt header next to the address.',
    )
