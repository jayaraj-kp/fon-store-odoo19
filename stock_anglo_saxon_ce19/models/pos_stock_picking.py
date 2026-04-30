# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Hooks into pos.order to create Anglo-Saxon delivery valuation entries.
POS validates pickings internally via _create_picking() which calls
stock.picking._action_done() at move level - bypassing our picking hooks.
So we hook pos.order.action_pos_order_paid() which runs AFTER picking is done.
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def action_pos_order_paid(self):
        """
        Override action_pos_order_paid to create delivery valuation entries
        after POS picking is validated.
        """
        res = super().action_pos_order_paid()
        self._create_anglo_saxon_delivery_entries()
        return res

    def _create_anglo_saxon_delivery_entries(self):
        """Create DR 121200 / CR 110100 entries for POS outgoing pickings."""
        for order in self:
            # Reload pickings after super() has created/validated them
            order.invalidate_recordset(['picking_ids'])
            pickings = order.picking_ids.filtered(
                lambda p: p.state == 'done'
                and p.picking_type_code == 'outgoing'
                and not p.delivery_journal_entry_ids
            )
            _logger.info(
                "Anglo-Saxon POS: order '%s' has %d outgoing done pickings",
                order.name, len(pickings)
            )
            for picking in pickings:
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon POS: Created delivery valuation for "
                        "picking '%s' (order '%s')",
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
        """
        Fallback hook - catches any outgoing pickings validated via _action_done.
        Works for both POS and other flows that bypass button_validate.
        """
        res = super()._action_done()
        for picking in self:
            if picking.state == 'done' \
                    and picking.picking_type_code == 'outgoing' \
                    and not picking.delivery_journal_entry_ids:
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon _action_done hook: Created delivery "
                        "valuation for picking '%s'", picking.name
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon _action_done hook: Failed for '%s': %s",
                        picking.name, str(e), exc_info=True
                    )
        return res