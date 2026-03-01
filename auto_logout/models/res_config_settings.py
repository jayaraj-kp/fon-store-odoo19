from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_logout_delay = fields.Integer(
        string='Auto Logout Delay (minutes)',
        default=10,
        config_parameter='auto_logout.delay',
        help='Number of minutes of inactivity before automatic logout. Set 0 to disable.'
    )
