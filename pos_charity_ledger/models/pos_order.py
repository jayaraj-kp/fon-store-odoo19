# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
    charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')
    charity_donation_id = fields.Many2one('pos.charity.donation', string='Donation Record', readonly=True)

    def _create_charity_donation(self):
        self.ensure_one()
        if self.charity_donation_amount > 0 and self.charity_account_id:
            try:
                donation = self.env['pos.charity.donation'].create({
                    'charity_account_id': self.charity_account_id.id,
                    'pos_session_id': self.session_id.id,
                    'pos_order_id': self.id,
                    'amount': self.charity_donation_amount,
                    'cashier_id': self.user_id.id,
                    'state': 'confirmed',
                    'note': f'Donation from POS Order {self.name}',
                })
                self.charity_donation_id = donation.id
                _logger.info('Charity donation of %s created for order %s',
                             self.charity_donation_amount, self.name)
            except Exception as e:
                _logger.error('Failed to create charity donation: %s', str(e))

    def _process_order(self, order, existing_order):
        order_id = super()._process_order(order, existing_order)
        charity_amount = order.get('charity_donation_amount', 0.0)
        charity_account_id = order.get('charity_account_id', False)
        if charity_amount and charity_amount > 0 and charity_account_id:
            pos_order = self.browse(order_id)
            if pos_order.exists():
                pos_order.write({
                    'charity_donation_amount': charity_amount,
                    'charity_account_id': charity_account_id,
                })
                pos_order._create_charity_donation()
        return order_id
