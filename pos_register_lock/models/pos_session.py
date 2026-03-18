# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class PosSession(models.Model):
    _inherit = 'pos.session'

    register_locked = fields.Boolean(
        string='Register Locked',
        default=False,
        copy=False,
        help="When True, the cashier cannot change amounts or close. "
             "A manager must unlock from the backend after reviewing excess/short.",
    )
    locked_by_id = fields.Many2one(
        'res.users',
        string='Locked By',
        readonly=True,
        copy=False,
    )
    locked_at = fields.Datetime(
        string='Locked At',
        readonly=True,
        copy=False,
    )

    def action_lock_register(self):
        """
        Called from POS frontend when cashier clicks 'Close Register'.
        Locks the session so the cashier cannot edit amounts or proceed to close.
        Manager must review excess/short in backend and unlock.
        """
        self.ensure_one()
        if self.state not in ('opened',):
            raise exceptions.UserError(_("Can only lock an open session."))
        self.write({
            'register_locked': True,
            'locked_by_id': self.env.uid,
            'locked_at': fields.Datetime.now(),
        })
        return True

    def action_unlock_register(self):
        """
        Called by manager from backend to unlock the register
        after reviewing excess/short amounts.
        Once unlocked, the cashier can proceed to close normally.
        """
        self.ensure_one()
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise exceptions.UserError(
                _("Only a POS Manager can unlock the register.")
            )
        self.write({
            'register_locked': False,
            'locked_by_id': False,
            'locked_at': False,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Register Unlocked'),
                'message': _(
                    'The register has been unlocked after reviewing the amounts. '
                    'The cashier can now proceed to close.'
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _loader_params_pos_session(self):
        """Include register_locked in the fields loaded into the POS frontend."""
        result = super()._loader_params_pos_session()
        result['search_params']['fields'].append('register_locked')
        return result
