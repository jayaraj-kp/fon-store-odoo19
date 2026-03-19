# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(
        string='Charity Donation',
        default=0.0,
        help='Amount donated to charity from this order.',
    )
    charity_account_id = fields.Many2one(
        'pos.charity.account',
        string='Charity Account',
    )
    charity_donation_id = fields.Many2one(
        'pos.charity.donation',
        string='Donation Record',
        readonly=True,
    )

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Override to create charity donation record when order is processed."""
        order_id = super()._process_order(order, draft, existing_order)

        charity_amount = order.get('charity_donation_amount', 0.0)
        charity_account_id = order.get('charity_account_id', False)

        if charity_amount and charity_amount > 0 and charity_account_id:
            pos_order = self.browse(order_id)
            try:
                donation = self.env['pos.charity.donation'].create({
                    'charity_account_id': charity_account_id,
                    'pos_session_id': pos_order.session_id.id,
                    'pos_order_id': pos_order.id,
                    'amount': charity_amount,
                    'cashier_id': pos_order.user_id.id,
                    'state': 'confirmed',
                    'note': f'Donation from POS Order {pos_order.name}',
                })
                pos_order.write({
                    'charity_donation_amount': charity_amount,
                    'charity_account_id': charity_account_id,
                    'charity_donation_id': donation.id,
                })
                _logger.info(
                    'Charity donation of %s created for order %s',
                    charity_amount, pos_order.name
                )
            except Exception as e:
                _logger.error('Failed to create charity donation: %s', str(e))

        return order_id

    @api.model
    def create_charity_donation_from_pos(self, vals):
        """
        Called directly from the POS frontend via RPC.
        Creates a charity donation record.
        Returns the donation id.
        """
        donation = self.env['pos.charity.donation'].create({
            'charity_account_id': vals.get('charity_account_id'),
            'pos_session_id': vals.get('session_id'),
            'pos_order_id': vals.get('order_id'),
            'amount': vals.get('amount'),
            'cashier_id': self.env.user.id,
            'state': 'confirmed',
            'note': vals.get('note', ''),
        })
        return donation.id
