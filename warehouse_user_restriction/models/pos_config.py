# import logging
# from odoo import models, fields, api
#
# _logger = logging.getLogger(__name__)
#
#
# class PosConfig(models.Model):
#     _inherit = 'pos.config'
#
#     def open_ui(self):
#         """Clean up any stuck opening_control sessions before opening."""
#         self.ensure_one()
#         _logger.info("WHR_DEBUG open_ui called for config: %s (id=%s)", self.name, self.id)
#
#         # Find and delete any stuck sessions in opening_control state for this config
#         stuck_sessions = self.env['pos.session'].sudo().search([
#             ('config_id', '=', self.id),
#             ('state', '=', 'opening_control'),
#         ])
#         if stuck_sessions:
#             _logger.info("WHR_DEBUG Found %s stuck sessions, deleting: %s", len(stuck_sessions), stuck_sessions.ids)
#             stuck_sessions.sudo().unlink()
#
#         return super().open_ui()
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         user = self.env.user
#         if user._is_superuser():
#             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
#         if user.allowed_warehouse_ids:
#             allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
#             if allowed_wh_ids:
#                 self.env.cr.execute("""
#                     SELECT pc.id
#                     FROM pos_config pc
#                     LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
#                     WHERE spt.warehouse_id IN %s
#                 """, (allowed_wh_ids,))
#                 allowed_ids = [row[0] for row in self.env.cr.fetchall()]
#                 _logger.info("WHR_DEBUG allowed POS config ids: %s", allowed_ids)
#                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
#         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
#
#
# class PosSession(models.Model):
#     _inherit = 'pos.session'
#
#     @api.model
#     def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
#         user = self.env.user
#         if user._is_superuser():
#             return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
#         if user.allowed_warehouse_ids:
#             allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
#             if allowed_wh_ids:
#                 self.env.cr.execute("""
#                     SELECT ps.id
#                     FROM pos_session ps
#                     JOIN pos_config pc ON pc.id = ps.config_id
#                     LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
#                     WHERE spt.warehouse_id IN %s
#                 """, (allowed_wh_ids,))
#                 allowed_ids = [row[0] for row in self.env.cr.fetchall()]
#                 _logger.info("WHR_DEBUG allowed POS session ids: %s", allowed_ids)
#                 domain = list(domain) + [('id', 'in', allowed_ids or [0])]
#         return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
import logging
from odoo import models, api
_logger = logging.getLogger(__name__)

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        self.ensure_one()
        _logger.info("WHR_DEBUG open_ui called for config: %s (id=%s)", self.name, self.id)
        stuck_sessions = self.env['pos.session'].sudo().search([
            ('config_id', '=', self.id),
            ('state', '=', 'opening_control'),
        ])
        if stuck_sessions:
            _logger.info("WHR_DEBUG Found %s stuck sessions, deleting: %s", len(stuck_sessions), stuck_sessions.ids)
            stuck_sessions.sudo().unlink()
        return super().open_ui()

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
            if allowed_wh_ids:
                self.env.cr.execute("""
                    SELECT pc.id FROM pos_config pc
                    LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
                    WHERE spt.warehouse_id IN %s
                """, (allowed_wh_ids,))
                allowed_ids = [row[0] for row in self.env.cr.fetchall()]
                _logger.info("WHR_DEBUG allowed POS config ids: %s", allowed_ids)
                domain = list(domain) + [('id', 'in', allowed_ids or [0])]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _get_allowed_session_ids(self, user):
        """Return session IDs the user is allowed to access based on warehouse."""
        if user._is_superuser() or not user.allowed_warehouse_ids:
            return None  # No restriction
        allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
        if not allowed_wh_ids:
            return []
        self.env.cr.execute("""
            SELECT ps.id FROM pos_session ps
            JOIN pos_config pc ON pc.id = ps.config_id
            LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
            WHERE spt.warehouse_id IN %s
        """, (allowed_wh_ids,))
        return [row[0] for row in self.env.cr.fetchall()]

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        allowed_ids = self._get_allowed_session_ids(user)
        if allowed_ids is not None:
            _logger.info("WHR_DEBUG allowed POS session ids: %s", allowed_ids)
            domain = list(domain) + [('id', 'in', allowed_ids or [0])]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    def read(self, fields=None, load='_classic_read'):
        """Bypass ir.rule for sessions the user is warehouse-allowed to access."""
        user = self.env.user
        allowed_ids = self._get_allowed_session_ids(user)
        if allowed_ids is not None and set(self.ids).issubset(set(allowed_ids)):
            return super(PosSession, self.sudo()).read(fields=fields, load=load)
        return super().read(fields=fields, load=load)