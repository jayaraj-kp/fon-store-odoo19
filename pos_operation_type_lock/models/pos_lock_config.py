from odoo import models, fields, api, _
from odoo.exceptions import UserError
import hashlib


class PosOperationTypeLockConfig(models.Model):
    _name = 'pos.operation.type.lock.config'
    _description = 'POS Operation Type Lock Configuration'

    name = fields.Char(string='Name', default='POS Lock Configuration')
    lock_password = fields.Char(
        string='Lock Password',
        help='Password required to change the POS Operation Type'
    )
    is_locked = fields.Boolean(
        string='Lock Operation Type',
        default=True,
        help='When enabled, a password is required to change the Operation Type in POS settings'
    )

    @api.model
    def get_lock_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({'name': 'POS Lock Configuration', 'is_locked': True})
        return config

    def verify_password(self, password):
        """Verify if the provided password matches the stored password."""
        config = self.get_lock_config()
        if not config.lock_password:
            raise UserError(_('No lock password has been set. Please set a password first in POS Lock Configuration.'))
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        hashed_stored = hashlib.sha256(config.lock_password.encode()).hexdigest()
        return hashed_input == hashed_stored

    @api.model
    def check_and_verify_password(self, password):
        """Called from JS to verify password. Returns True/False."""
        config = self.get_lock_config()
        if not config.is_locked:
            return {'success': True, 'message': 'Lock is disabled'}
        if not config.lock_password:
            return {'success': False, 'message': _('No lock password set. Please configure it first.')}
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        hashed_stored = hashlib.sha256(config.lock_password.encode()).hexdigest()
        if hashed_input == hashed_stored:
            return {'success': True, 'message': _('Password verified successfully')}
        else:
            return {'success': False, 'message': _('Incorrect password. Access denied.')}

    @api.model
    def is_operation_type_locked(self):
        """Check if the operation type lock is active."""
        config = self.get_lock_config()
        return {'is_locked': config.is_locked, 'has_password': bool(config.lock_password)}
