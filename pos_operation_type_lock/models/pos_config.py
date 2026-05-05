from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    operation_type_locked = fields.Boolean(
        string='Operation Type Locked',
        compute='_compute_operation_type_locked',
        store=False,
    )

    def _compute_operation_type_locked(self):
        lock_config = self.env['pos.operation.type.lock.config'].get_lock_config()
        for record in self:
            record.operation_type_locked = lock_config.is_locked

    def write(self, vals):
        """Override write to check password when operation type changes."""
        if 'picking_type_id' in vals:
            lock_config = self.env['pos.operation.type.lock.config'].get_lock_config()
            if lock_config.is_locked:
                # Check if the context has the unlock flag
                if not self.env.context.get('pos_operation_type_unlocked'):
                    raise UserError(
                        _('The Operation Type is locked. Please use the unlock button and enter the correct password to change it.')
                    )
        return super().write(vals)
