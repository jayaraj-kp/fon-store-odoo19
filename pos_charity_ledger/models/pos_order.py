# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    charity_donation_amount = fields.Float(string='Charity Donation', default=0.0)
    charity_account_id = fields.Many2one('pos.charity.account', string='Charity Account')

    def _process_order(self, order, existing_order):
        charity_amount = order.get('charity_donation_amount', 0.0) or 0.0
        charity_account_id = order.get('charity_account_id', False)
        order_id = super()._process_order(order, existing_order)

        if charity_amount > 0 and charity_account_id:
            pos_order = self.browse(order_id)
            if pos_order.exists():
                pos_order.write({
                    'charity_donation_amount': charity_amount,
                    'charity_account_id': charity_account_id,
                })
                # Accumulate on the session — do NOT post to ledger yet.
                # The ledger entry is created when the register is closed.
                session = pos_order.session_id
                if session:
                    session.add_charity_pending_amount(charity_amount)
                    _logger.info(
                        'Order %s added %s charity to session %s pending total',
                        pos_order.name, charity_amount, session.name,
                    )

        return order_id
