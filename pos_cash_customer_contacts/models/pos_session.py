from odoo import models
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_partners_domain(self):
        """
        Odoo 19: This method exists but returns [] by default.
        Not the main filter — partner loading is done via
        res.partner._load_pos_data_domain and get_new_partner.
        Kept here for safety/future compatibility.
        """
        return super()._get_partners_domain()