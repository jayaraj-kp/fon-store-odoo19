# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Hooks into POS order processing to create Anglo-Saxon
delivery valuation entries (DR 121200 / CR 110100).

Odoo 19 POS flow:
  sync_from_ui
    -> _process_order
       -> _process_saved_order
          -> action_pos_order_paid   (invoice/payment)
          -> _create_order_picking   (picking created HERE)

So we must hook AFTER _create_order_picking, i.e. at end of _process_saved_order.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _process_saved_order(self, draft):
        """
        Hook after _create_order_picking() to create delivery valuation.
        In Odoo 19, picking is created inside this method AFTER
        action_pos_order_paid(), so we run our logic at the very end.
        """
        res = super()._process_saved_order(draft)
        _logger.info(
            "Anglo-Saxon POS: _process_saved_order called for '%s' draft=%s",
            self.name, draft
        )
        if not draft:
            self._create_anglo_saxon_pos_delivery_entries()
        return res

    def _create_anglo_saxon_pos_delivery_entries(self):
        """Create DR 121200 / CR 110100 for POS outgoing pickings."""
        for order in self:
            _logger.info(
                "Anglo-Saxon POS: checking order '%s' picking_ids=%s",
                order.name,
                order.picking_ids.mapped('name')
            )
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
        """Fallback hook via stock move level for non-POS outgoing pickings."""
        res = super()._action_done()
        for picking in self:
            if picking.state == 'done' \
                    and picking.picking_type_code == 'outgoing' \
                    and not picking.delivery_journal_entry_ids:
                # Skip POS pickings - handled by _process_saved_order above
                if picking.pos_order_id:
                    continue
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
