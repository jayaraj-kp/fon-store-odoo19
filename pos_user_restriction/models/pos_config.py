# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    allowed_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='pos_config_users_rel',
        column1='pos_config_id',
        column2='user_id',
        string='Allowed Users',
        help="Users who are allowed to access this POS terminal. "
             "This is the reverse of Allowed POS on the user form.",
    )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """Override _search to filter POS configs based on user restrictions."""
        result = super()._search(
            domain, offset=offset, limit=limit, order=order,
            access_rights_uid=access_rights_uid
        )
        return result

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **kwargs):
        """Filter search_read results for non-admin users with POS restrictions."""
        user = self.env.user
        # Skip restriction for superuser / POS Manager
        if not user._is_pos_restricted():
            return super().search_read(domain=domain, fields=fields, offset=offset,
                                       limit=limit, order=order, **kwargs)
        allowed_ids = user.allowed_pos_ids.ids
        if domain is None:
            domain = []
        domain = [('id', 'in', allowed_ids)] + list(domain)
        return super().search_read(domain=domain, fields=fields, offset=offset,
                                   limit=limit, order=order, **kwargs)

    def open_ui(self):
        """Check if the current user is allowed to open this POS."""
        self._check_pos_access()
        return super().open_ui()

    def open_session_cb(self, check_coa=True):
        """Check if the current user is allowed to open a session."""
        self._check_pos_access()
        return super().open_session_cb(check_coa=check_coa)

    def _check_pos_access(self):
        """Raise an error if the current user is not allowed to access this POS."""
        user = self.env.user
        if user._is_pos_restricted():
            for pos in self:
                if pos not in user.allowed_pos_ids:
                    raise exceptions.UserError(
                        _("You are not allowed to access the Point of Sale '%s'.\n"
                          "Please contact your administrator to grant you access.")
                        % pos.name
                    )


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _is_pos_restricted(self):
        """Return True if this user has POS restrictions configured."""
        self.ensure_one()
        # Superuser and internal admin users with no restrictions → no filter
        if self._is_superuser():
            return False
        # POS Manager group → no restriction (they manage everything)
        pos_manager_group = self.env.ref('point_of_sale.group_pos_manager', raise_if_not_found=False)
        if pos_manager_group and pos_manager_group in self.groups_id:
            return False
        # If allowed_pos_ids is set → restricted
        return bool(self.allowed_pos_ids)
