from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_gender = fields.Selection(
        selection=[('male', 'Male'), ('female', 'Female')],
        string="Gender",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Include x_gender in the POS data bundle so it is available
        on partner records in the frontend."""
        fields = super()._load_pos_data_fields(config_id)
        fields += ['x_gender']
        return fields
