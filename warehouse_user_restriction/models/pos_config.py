# # import logging
# # from odoo import models, api
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class PosConfig(models.Model):
# #     _inherit = 'pos.config'
# #
# #     def open_ui(self):
# #         """Clean up any stuck opening_control sessions before opening."""
# #         self.ensure_one()
# #         _logger.info("WHR_DEBUG open_ui called for config: %s (id=%s)", self.name, self.id)
# #
# #         stuck_sessions = self.env['pos.session'].sudo().search([
# #             ('config_id', '=', self.id),
# #             ('state', '=', 'opening_control'),
# #         ])
# #         if stuck_sessions:
# #             _logger.info("WHR_DEBUG Found %s stuck sessions, deleting: %s", len(stuck_sessions), stuck_sessions.ids)
# #             stuck_sessions.sudo().unlink()
# #
# #         return super().open_ui()
# #
# #     def _user_has_pos_restriction(self, user):
# #         """
# #         Check via raw SQL whether the user has explicit POS terminal restrictions
# #         set by the pos_user_restriction module.
# #         If yes, that module handles all POS filtering — skip warehouse filter entirely.
# #         """
# #         try:
# #             self.env.cr.execute(
# #                 "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
# #                 (user.id,)
# #             )
# #             return bool(self.env.cr.fetchone())
# #         except Exception:
# #             return False
# #
# #     @api.model
# #     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
# #         user = self.env.user
# #
# #         if user._is_superuser():
# #             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# #         # If user has explicit POS restrictions, skip warehouse filter
# #         if self._user_has_pos_restriction(user):
# #             _logger.info("WHR_DEBUG user %s has explicit POS restriction, skipping warehouse filter", user.id)
# #             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# #         if user.allowed_warehouse_ids:
# #             allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
# #             if allowed_wh_ids:
# #                 self.env.cr.execute("""
# #                     SELECT pc.id
# #                     FROM pos_config pc
# #                     LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
# #                     WHERE spt.warehouse_id IN %s
# #                 """, (allowed_wh_ids,))
# #                 allowed_ids = [row[0] for row in self.env.cr.fetchall()]
# #                 _logger.info("WHR_DEBUG allowed POS config ids: %s", allowed_ids)
# #                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
# #
# #         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# #
# # class PosSession(models.Model):
# #     _inherit = 'pos.session'
# #
# #     def _user_has_pos_restriction(self, user):
# #         """
# #         Check via raw SQL whether the user has explicit POS terminal restrictions.
# #         Replicates the check from PosConfig so PosSession can use it independently.
# #         """
# #         try:
# #             self.env.cr.execute(
# #                 "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
# #                 (user.id,)
# #             )
# #             return bool(self.env.cr.fetchone())
# #         except Exception:
# #             return False
# #
# #     @api.model
# #     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
# #         user = self.env.user
# #
# #         if user._is_superuser():
# #             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# #         # If user has explicit POS restrictions, skip warehouse session filter.
# #         # The pos_user_restriction module controls which configs they can access,
# #         # so sessions must NOT be filtered by warehouse — that causes KeyError: False
# #         # in point_of_sale/controllers/main.py when loading the POS UI.
# #         if self._user_has_pos_restriction(user):
# #             _logger.info("WHR_DEBUG user %s has explicit POS restriction, skipping session warehouse filter", user.id)
# #             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# #         if user.allowed_warehouse_ids:
# #             allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
# #             if allowed_wh_ids:
# #                 self.env.cr.execute("""
# #                     SELECT ps.id
# #                     FROM pos_session ps
# #                     JOIN pos_config pc ON pc.id = ps.config_id
# #                     LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
# #                     WHERE spt.warehouse_id IN %s
# #                 """, (allowed_wh_ids,))
# #                 allowed_ids = [row[0] for row in self.env.cr.fetchall()]
# #                 _logger.info("WHR_DEBUG allowed POS session ids: %s", allowed_ids)
# #                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
# #
# #         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
# #
# import logging
# from odoo import models, api
#
# _logger = logging.getLogger(__name__)
#
#
# # ─────────────────────────────────────────────────────────────────────────────
# # Request-level cache helper
# #
# # Problem:  _search() is called 20-30 times per POS page load.
# #           Each call ran 2 SQL queries → 40-60 extra queries per request.
# #           This caused the POS lag seen in logs (WHR_DEBUG spam).
# #
# # Fix:      Store results in a dict on the DB cursor (cr._whr_cache).
# #           The cursor is created per-request and discarded after, so this
# #           cache is 100% request-scoped — no stale data across requests.
# #
# # Workflow: ALL restriction logic is IDENTICAL to the original.
# #           Only change: SQL runs once per request instead of 20-30 times.
# # ─────────────────────────────────────────────────────────────────────────────
#
# def _get_request_cache(cr):
#     """Return a per-request dict attached to the DB cursor."""
#     if not hasattr(cr, '_whr_cache'):
#         cr._whr_cache = {}
#     return cr._whr_cache
#
#
# def _cache_key(prefix, user_id):
#     return '%s_%s' % (prefix, user_id)
#
#
# class PosConfig(models.Model):
#     _inherit = 'pos.config'
#
#     def open_ui(self):
#         """Clean up any stuck opening_control sessions before opening."""
#         self.ensure_one()
#         _logger.info("WHR open_ui called for config: %s (id=%s)", self.name, self.id)
#
#         stuck_sessions = self.env['pos.session'].sudo().search([
#             ('config_id', '=', self.id),
#             ('state', '=', 'opening_control'),
#         ])
#         if stuck_sessions:
#             _logger.info("WHR Found %s stuck sessions, deleting: %s",
#                          len(stuck_sessions), stuck_sessions.ids)
#             stuck_sessions.sudo().unlink()
#
#         return super().open_ui()
#
#     def _user_has_pos_restriction(self, user):
#         """
#         Check whether the user has explicit POS terminal restrictions
#         set by the pos_user_restriction module.
#         If yes, that module handles all POS filtering — skip warehouse filter entirely.
#
#         SAME logic as original — adds request-level cache so SQL runs once per request.
#         """
#         cache = _get_request_cache(self.env.cr)
#         key = _cache_key('pos_restriction', user.id)
#         if key in cache:
#             return cache[key]
#
#         try:
#             self.env.cr.execute(
#                 "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
#                 (user.id,)
#             )
#             result = bool(self.env.cr.fetchone())
#         except Exception:
#             result = False
#
#         cache[key] = result
#         return result
#
#     def _get_allowed_pos_config_ids(self, user):
#         """
#         Return allowed POS config ids for the user's warehouses.
#         SAME SQL as original — adds request-level cache so SQL runs once per request.
#         """
#         cache = _get_request_cache(self.env.cr)
#         key = _cache_key('allowed_pos_config_ids', user.id)
#         if key in cache:
#             return cache[key]
#
#         allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
#         if not allowed_wh_ids:
#             cache[key] = None
#             return None
#
#         self.env.cr.execute("""
#             SELECT pc.id
#             FROM pos_config pc
#             LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
#             WHERE spt.warehouse_id IN %s
#         """, (allowed_wh_ids,))
#         allowed_ids = [row[0] for row in self.env.cr.fetchall()]
#         _logger.info("WHR allowed POS config ids for user %s: %s", user.id, allowed_ids)
#
#         cache[key] = allowed_ids
#         return allowed_ids
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         user = self.env.user
#
#         if user._is_superuser():
#             return super()._search(domain, offset=offset, limit=limit,
#                                    order=order, **kwargs)
#
#         # If user has explicit POS restrictions, skip warehouse filter
#         # (pos_user_restriction module handles filtering for these users)
#         if self._user_has_pos_restriction(user):
#             _logger.debug("WHR user %s has explicit POS restriction, skipping warehouse filter",
#                           user.id)
#             return super()._search(domain, offset=offset, limit=limit,
#                                    order=order, **kwargs)
#
#         if user.allowed_warehouse_ids:
#             allowed_ids = self._get_allowed_pos_config_ids(user)
#             if allowed_ids is not None:
#                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
#
#         return super()._search(domain, offset=offset, limit=limit,
#                                order=order, **kwargs)
#
#
# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     def _user_has_pos_restriction(self, user):
#         """
#         Same check as PosConfig._user_has_pos_restriction.
#         Shares the same request-level cache key so SQL fires only ONCE
#         per request regardless of which class calls it first.
#         """
#         cache = _get_request_cache(self.env.cr)
#         key = _cache_key('pos_restriction', user.id)
#         if key in cache:
#             return cache[key]
#
#         try:
#             self.env.cr.execute(
#                 "SELECT 1 FROM pos_config_users_rel WHERE user_id = %s LIMIT 1",
#                 (user.id,)
#             )
#             result = bool(self.env.cr.fetchone())
#         except Exception:
#             result = False
#
#         cache[key] = result
#         return result
#
#     def _get_allowed_pos_session_ids(self, user):
#         """
#         Return allowed POS session ids for the user's warehouses.
#         SAME SQL as original — adds request-level cache so SQL runs once per request.
#         """
#         cache = _get_request_cache(self.env.cr)
#         key = _cache_key('allowed_pos_session_ids', user.id)
#         if key in cache:
#             return cache[key]
#
#         allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
#         if not allowed_wh_ids:
#             cache[key] = None
#             return None
#
#         self.env.cr.execute("""
#             SELECT ps.id
#             FROM pos_session ps
#             JOIN pos_config pc ON pc.id = ps.config_id
#             LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
#             WHERE spt.warehouse_id IN %s
#         """, (allowed_wh_ids,))
#         allowed_ids = [row[0] for row in self.env.cr.fetchall()]
#         _logger.info("WHR allowed POS session ids for user %s: %s", user.id, allowed_ids)
#
#         cache[key] = allowed_ids
#         return allowed_ids
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         user = self.env.user
#
#         if user._is_superuser():
#             return super()._search(domain, offset=offset, limit=limit,
#                                    order=order, **kwargs)
#
#         # If user has explicit POS restrictions, skip warehouse session filter.
#         # The pos_user_restriction module controls which configs they can access,
#         # so sessions must NOT be filtered by warehouse — that causes KeyError: False
#         # in point_of_sale/controllers/main.py when loading the POS UI.
#         if self._user_has_pos_restriction(user):
#             _logger.debug("WHR user %s has explicit POS restriction, skipping session warehouse filter",
#                           user.id)
#             return super()._search(domain, offset=offset, limit=limit,
#                                    order=order, **kwargs)
#
#         if user.allowed_warehouse_ids:
#             allowed_ids = self._get_allowed_pos_session_ids(user)
#             if allowed_ids is not None:
#                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
#
#         return super()._search(domain, offset=offset, limit=limit,
#                                order=order, **kwargs)
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
        """
        Check whether the user has explicit POS terminal restrictions
        set by the pos_user_restriction module.
        If yes, that module handles all POS filtering — skip warehouse filter entirely.

        Cached per-request so the SQL runs once regardless of how many times
        _search() is called during a single page load.
        """
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
        """
        Return allowed POS config ids for the user's warehouses.
        Cached per-request — SQL runs once per request instead of on every
        _search() call.
        """
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

        # If user has explicit POS restrictions, skip warehouse filter
        # (pos_user_restriction module handles filtering for these users)
        if self._user_has_pos_restriction(user):
            _logger.debug("WHR user %s has explicit POS restriction, skipping warehouse filter",
                          user.id)
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
        """
        Same check as PosConfig._user_has_pos_restriction.
        Shares the same request-level cache key so SQL fires only ONCE
        per request regardless of which class calls it first.
        """
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

    def _get_allowed_pos_session_ids(self, user):
        """
        Return allowed POS session ids for the user's warehouses.

        OPTIMIZATION vs. original: this used to fetch EVERY historical
        session (open and closed, going back to day 1) on every request,
        producing lists of 600+ ids that grow forever and get logged in
        full each time — this was a major contributor to the POS lag.

        Now: closed sessions older than 60 days are excluded, since a
        closed session from months ago never needs to appear in this
        filter again. Still cached per-request on top of that.
        """
        cache = get_request_cache(self.env.cr)
        key = cache_key('allowed_pos_session_ids', user.id)
        if key in cache:
            return cache[key]

        allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
        if not allowed_wh_ids:
            cache[key] = None
            return None

        self.env.cr.execute("""
            SELECT ps.id
            FROM pos_session ps
            JOIN pos_config pc ON pc.id = ps.config_id
            LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
            WHERE spt.warehouse_id IN %s
              AND (ps.state != 'closed' OR ps.start_at >= NOW() - INTERVAL '60 days')
        """, (allowed_wh_ids,))
        allowed_ids = [row[0] for row in self.env.cr.fetchall()]
        _logger.info("WHR allowed POS session ids for user %s: %s sessions",
                     user.id, len(allowed_ids))

        cache[key] = allowed_ids
        return allowed_ids

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user

        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        # If user has explicit POS restrictions, skip warehouse session filter.
        # The pos_user_restriction module controls which configs they can access,
        # so sessions must NOT be filtered by warehouse — that causes KeyError: False
        # in point_of_sale/controllers/main.py when loading the POS UI.
        if self._user_has_pos_restriction(user):
            _logger.debug("WHR user %s has explicit POS restriction, skipping session warehouse filter",
                          user.id)
            return super()._search(domain, offset=offset, limit=limit,
                                   order=order, **kwargs)

        if user.allowed_warehouse_ids:
            allowed_ids = self._get_allowed_pos_session_ids(user)
            if allowed_ids is not None:
                domain = list(domain) + [('id', 'in', allowed_ids or [0])]

        return super()._search(domain, offset=offset, limit=limit,
                               order=order, **kwargs)