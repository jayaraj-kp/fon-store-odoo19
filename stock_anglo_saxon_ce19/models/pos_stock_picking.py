# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Hooks into POS order processing to create Anglo-Saxon
delivery valuation entries (DR 121200 / CR 110100).
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """
        Odoo 19 POS uses _process_saved_order() after syncing from UI.
        Hook here to create delivery valuation after picking is done.
        """
        res = super()._process_saved_order(draft)
        if not draft:
            self._create_anglo_saxon_pos_delivery_entries()
        return res

    def action_pos_order_paid(self):
        """Fallback hook for older Odoo 19 builds."""
        res = super().action_pos_order_paid()
        self._create_anglo_saxon_pos_delivery_entries()
        return res

    def _create_anglo_saxon_pos_delivery_entries(self):
        """Create DR 121200 / CR 110100 for POS outgoing pickings."""
        for order in self:
            try:
                order.invalidate_recordset(['picking_ids'])
            except Exception:
                pass

            pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done'
                          and p.picking_type_code == 'outgoing'
                          and not p.delivery_journal_entry_ids
            )

            _logger.info(
                "Anglo-Saxon POS: order '%s' found %d eligible pickings",
                order.name, len(pickings)
            )

            for picking in pickings:
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon POS: Created delivery valuation "
                        "for picking '%s' (order '%s')",
                        picking.name, order.name
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon POS: Failed for picking '%s': %s",
                        picking.name, str(e), exc_info=True
                    )


class StockPickingPos(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """Additional fallback via stock move level."""
        res = super()._action_done()
        for picking in self:
            if picking.state == 'done' \
                    and picking.picking_type_code == 'outgoing' \
                    and not picking.delivery_journal_entry_ids:
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon _action_done: Created delivery "
                        "valuation for '%s'", picking.name
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon _action_done: Failed '%s': %s",
                        picking.name, str(e), exc_info=True
                    )
        return res