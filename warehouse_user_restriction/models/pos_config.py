import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        _logger.info("WHR_DEBUG PosConfig._search called by user: %s (id=%s)", user.name, user.id)
        _logger.info("WHR_DEBUG user.allowed_warehouse_ids: %s", user.allowed_warehouse_ids.ids if not user._is_superuser() else 'SUPERUSER')

        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

        if user.allowed_warehouse_ids:
            allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
            if allowed_wh_ids:
                self.env.cr.execute("""
                    SELECT pc.id
                    FROM pos_config pc
                    LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
                    WHERE spt.warehouse_id IN %s
                """, (allowed_wh_ids,))
                allowed_ids = [row[0] for row in self.env.cr.fetchall()]
                _logger.info("WHR_DEBUG allowed POS config ids: %s", allowed_ids)
                domain = list(domain) + [('id', 'in', allowed_ids or [0])]

        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        _logger.info("WHR_DEBUG PosSession._search called by user: %s (id=%s)", user.name, user.id)

        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

        if user.allowed_warehouse_ids:
            allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
            if allowed_wh_ids:
                self.env.cr.execute("""
                    SELECT ps.id
                    FROM pos_session ps
                    JOIN pos_config pc ON pc.id = ps.config_id
                    LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
                    WHERE spt.warehouse_id IN %s
                """, (allowed_wh_ids,))
                allowed_ids = [row[0] for row in self.env.cr.fetchall()]
                _logger.info("WHR_DEBUG allowed POS session ids: %s", allowed_ids)
                domain = list(domain) + [('id', 'in', allowed_ids or [0])]

        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)

    def _check_pos_session_validity(self):
        """Log before session validity check to debug 'another session' error."""
        _logger.info("WHR_DEBUG _check_pos_session_validity called for session: %s state: %s config: %s",
                     self.id, self.state, self.config_id.name)
        return super()._check_pos_session_validity()
