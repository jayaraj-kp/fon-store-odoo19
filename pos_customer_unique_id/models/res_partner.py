# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── Fields ───────────────────────────────────────────────────────────────
    pos_unique_id = fields.Char(
        string='POS Customer ID',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Unique sequential ID auto-generated when this contact is first created from POS.',
    )
    pos_config_id = fields.Many2one(
        comodel_name='pos.config',
        string='Created at Shop',
        readonly=True,
        copy=False,
        ondelete='set null',
        help='The POS shop/terminal from which this contact was originally created.',
    )

    # ── POS UI Integration ───────────────────────────────────────────────────
    @api.model
    def create_from_ui(self, partner):
        """
        Override the standard POS partner-save method to auto-generate
        a unique customer ID when a new partner is created from POS.

        The POS JS passes 'pos_config_id_for_uid' in the partner dict.
        We pop it before calling super() so it doesn't trigger a field error.
        """
        # Extract our custom field (not a real partner field)
        pos_config_id = partner.pop('pos_config_id_for_uid', False)
        is_new_partner = not partner.get('id', False)

        # Call the standard Odoo create_from_ui
        partner_id = super().create_from_ui(partner)

        # Generate unique ID only for NEW partners
        if is_new_partner and partner_id:
            config = self._resolve_pos_config(pos_config_id)
            if config and config.shop_code:
                try:
                    unique_id = config._get_next_customer_id()
                    if unique_id:
                        self.browse(partner_id).write({
                            'pos_unique_id': unique_id,
                            'pos_config_id': config.id,
                        })
                        _logger.info(
                            'POS Customer ID %s assigned to partner id=%s (shop: %s)',
                            unique_id, partner_id, config.name
                        )
                except Exception as e:
                    # Non-blocking: log the error but don't prevent partner creation
                    _logger.error(
                        'Failed to generate POS unique ID for partner %s: %s',
                        partner_id, e
                    )

        return partner_id

    def _resolve_pos_config(self, pos_config_id):
        """
        Find the POS config to use for ID generation.
        Priority:
          1. Explicit pos_config_id passed from POS UI (most reliable)
          2. Active POS session for the current user (fallback)
        """
        if pos_config_id:
            config = self.env['pos.config'].browse(int(pos_config_id))
            if config.exists():
                return config

        # Fallback: find any open POS session belonging to the current user
        session = self.env['pos.session'].search([
            ('state', '=', 'opened'),
            ('user_id', '=', self.env.uid),
        ], limit=1)
        if session and session.config_id:
            return session.config_id

        return None
