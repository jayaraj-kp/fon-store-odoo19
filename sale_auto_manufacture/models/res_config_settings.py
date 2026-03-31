from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_manufacture_on_confirm = fields.Boolean(
        string='Auto-Manufacture on Sale Confirm',
        help=(
            'When enabled, confirming a Sale Order will automatically:\n'
            '1. Create a Manufacturing Order for products with a BoM\n'
            '2. Confirm and produce the MO immediately\n'
            '3. Reduce component stock\n'
            '4. Increase finished product stock'
        ),
        config_parameter='sale_auto_manufacture.auto_manufacture_on_confirm',
    )
