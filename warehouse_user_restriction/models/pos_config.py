from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # Use Integer instead of Many2one to avoid POS IndexedDB TypeError
    # Many2one fields cause POS frontend to crash when loading model relations
    allowed_warehouse_id = fields.Integer(
        string='Linked Warehouse ID',
        help='Internal ID of the warehouse linked to this POS for user restriction.',
        default=0,
    )

    # Computed display field for the form view (not loaded by POS)
    allowed_warehouse_display = fields.Many2one(
        'stock.warehouse',
        string='Linked Warehouse',
        compute='_compute_allowed_warehouse_display',
        inverse='_inverse_allowed_warehouse_display',
        store=False,
    )

    def _compute_allowed_warehouse_display(self):
        for rec in self:
            if rec.allowed_warehouse_id:
                rec.allowed_warehouse_display = self.env['stock.warehouse'].browse(
                    rec.allowed_warehouse_id
                )
            else:
                rec.allowed_warehouse_display = False

    def _inverse_allowed_warehouse_display(self):
        for rec in self:
            rec.allowed_warehouse_id = rec.allowed_warehouse_display.id or 0

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            domain = list(domain) + [
                ('allowed_warehouse_id', 'in', allowed_wh_ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        user = self.env.user
        if user._is_superuser():
            return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
        if user.allowed_warehouse_ids:
            allowed_wh_ids = user.allowed_warehouse_ids.ids
            domain = list(domain) + [
                ('config_id.allowed_warehouse_id', 'in', allowed_wh_ids)
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
