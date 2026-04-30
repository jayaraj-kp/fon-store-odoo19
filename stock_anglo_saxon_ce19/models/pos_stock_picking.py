
# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Fires Anglo-Saxon delivery valuation entry for POS orders.
POS confirms stock moves via pos.order._create_picking(),
which calls stock.picking.button_validate() internally —
but the picking_type_code for POS is 'outgoing', so your
existing _create_delivery_valuation_entry() should fire.

If it's NOT firing, it means POS uses a different validation path.
This module forces it by hooking pos.order.action_pos_order_paid().
"""
import logging
from odoo import models, api

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        """After POS order is paid, trigger delivery valuation for its pickings."""
        res = super().action_pos_order_paid()
        for order in self:
            for picking in order.picking_ids.filtered(
                lambda p: p.state == 'done'
                and p.picking_type_code == 'outgoing'
                and not p.delivery_journal_entry_ids
            ):
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon POS: Created delivery valuation for "
                        "picking '%s' from POS order '%s'",
                        picking.name, order.name
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon POS: Failed for picking '%s': %s",
                        picking.name, str(e), exc_info=True
                    )
        return res