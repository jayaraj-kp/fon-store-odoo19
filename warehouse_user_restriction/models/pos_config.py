import logging
from odoo import models, api
from .utils import get_request_cache, cache_key

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        """Clean up any stuck opening_control sessions before opening."""
        self.ensure_one()
        _logger.info("WHR open_ui called for config: %s (id=%s)", self.name, self.id)

        stuck_sessions = self.env['pos.session'].sudo().search([
            ('config_id', '=', self.id),
            ('state', '=', 'opening_control'),
        ])
        if stuck_sessions:
            _logger.info("WHR Found %s stuck sessions, deleting: %s",
                         len(stuck_sessions), stuck_sessions.ids)
            stuck_sessions.sudo().unlink()

        return super().open_ui()

    def _user_has_pos_restriction(self, user):
        """Explicit POS terminal restriction (pos_user_restriction module)?
        Cached per request."""
        cache = get_request_cache(self.env.cr)
        key = cache_key('pos_restriction', user.id)
        if key in cache:
            return cache[key]

        try:
            self.env.cr.execute(
                "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
                (user.id,)
            )
            result = bool(self.env.cr.fetchone())
        except Exception:
            result = False

        cache[key] = result
        return result

    def _get_allowed_pos_config_ids(self, user):
        """POS config ids belonging to the user's allowed warehouses.
        Returns None when the user has no warehouse restriction.
        Cached per request."""
        cache = get_request_cache(self.env.cr)
        key = cache_key('allowed_pos_config_ids', user.id)
        if key in cache:
            return cache[key]

        allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
        if not allowed_wh_ids:
            cache[key] = None
            return None

        self.env.cr.execute("""
            SELECT pc.id
            FROM pos_config pc
            LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
            WHERE spt.warehouse_id IN %s
        """, (allowed_wh_ids,))
        allowed_ids = [row[0] for row in self.env.cr.fetchall()]
        _logger.info("WHR allowed POS config ids for user %s: %s", user.id, allowed_ids)

        cache[key] = allowed_ids
        return allowed_ids

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user

        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        if self._user_has_pos_restriction(user):
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        if user.allowed_warehouse_ids:
            allowed_ids = self._get_allowed_pos_config_ids(user)
            if allowed_ids is not None:
                domain = list(domain) + [('id', 'in', allowed_ids or [0])]

        return super()._search(domain, offset=offset, limit=limit,
                               order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _user_has_pos_restriction(self, user):
        """Same check as PosConfig (shares the same per-request cache key)."""
        cache = get_request_cache(self.env.cr)
        key = cache_key('pos_restriction', user.id)
        if key in cache:
            return cache[key]

        try:
            self.env.cr.execute(
                "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
                (user.id,)
            )
            result = bool(self.env.cr.fetchone())
        except Exception:
            result = False

        cache[key] = result
        return result

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user

        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        # Users with explicit POS terminal restrictions are handled by
        # pos_user_restriction; filtering sessions here breaks POS UI loading.
        if self._user_has_pos_restriction(user):
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        if user.allowed_warehouse_ids:
            # Filter by CONFIG, not by an enumerated list of session ids.
            # The config list is tiny and stable, so no session is ever
            # silently dropped (old closed sessions stay readable) and the
            # domain does not grow as sessions accumulate.
            config_ids = self.env['pos.config']._get_allowed_pos_config_ids(user)
            if config_ids is not None:
                domain = list(domain) + [('config_id', 'in', config_ids or [0])]

        return super()._search(domain, offset=offset, limit=limit,
                               order=order, **kwargs)