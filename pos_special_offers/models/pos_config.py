# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    show_special_offers_button = fields.Boolean(
        string='Show Special Offers Button',
        default=True,
        help='Display the Special Offers quick access button in the POS top menu bar.'
    )


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_loyalty_programs_for_pos(self):
        """
        Return all active loyalty/coupon programs linked to this POS config.
        Used by the frontend to display and manage offers.
        """
        self.ensure_one()
        programs = self.config_id.program_ids
        result = []
        for prog in programs:
            result.append({
                'id': prog.id,
                'name': prog.name,
                'program_type': prog.program_type,
                'trigger': prog.trigger,
                'applies_on': prog.applies_on,
                'reward_ids': [{
                    'id': r.id,
                    'reward_type': r.reward_type,
                    'discount': r.discount,
                    'description': r.description,
                } for r in prog.reward_ids],
            })
        return result
