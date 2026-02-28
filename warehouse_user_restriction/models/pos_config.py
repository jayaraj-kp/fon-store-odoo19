from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = tuple(user.allowed_warehouse_ids.ids)
            if allowed_wh_ids:
                # Use direct SQL to avoid recursive ORM call
                self.env.cr.execute("""
                    SELECT pc.id
                    FROM pos_config pc
                    LEFT JOIN stock_picking_type spt ON spt.id = pc.picking_type_id
                    WHERE spt.warehouse_id IN %s
                """, (allowed_wh_ids,))
                allowed_ids = [row[0] for row in self.env.cr.fetchall()]
                if allowed_ids:
                    domain = list(domain) + [('id', 'in', allowed_ids)]
                else:
                    domain = list(domain) + [('id', 'in', [0])]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
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
                if allowed_ids:
                    domain = list(domain) + [('id', 'in', allowed_ids)]
                else:
                    domain = list(domain) + [('id', 'in', [0])]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
