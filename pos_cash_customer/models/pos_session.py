# -*- coding: utf-8 -*-
from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'
    # No overrides needed — res.partner._load_pos_data_fields handles field injection.
