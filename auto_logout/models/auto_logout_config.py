from odoo import api, fields, models


class AutoLogoutConfig(models.TransientModel):
    """
    Singleton-style transient model to store auto logout configuration.
    Uses ir.config_parameter as persistent storage.
    Accessible via Technical > Auto Logout > Settings menu.
    """
    _name = 'auto.logout.config'
    _description = 'Auto Logout Configuration'

    logout_delay = fields.Integer(
        string='Session Timeout (minutes)',
        default=10,
        help='Number of minutes of inactivity before the user is automatically logged out. Set 0 to disable.'
    )

    @api.model
    def get_default_values(self):
        """Load current config from ir.config_parameter."""
        delay = int(self.env['ir.config_parameter'].sudo().get_param(
            'auto_logout.delay', default=10
        ))
        return self.create({'logout_delay': delay})

    def save_config(self):
        """Save settings to ir.config_parameter."""
        self.env['ir.config_parameter'].sudo().set_param(
            'auto_logout.delay', self.logout_delay
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Auto Logout',
                'message': f'Settings saved! Timeout set to {self.logout_delay} minute(s).',
                'type': 'success',
                'sticky': False,
            }
        }
