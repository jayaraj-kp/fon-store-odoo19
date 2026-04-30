# -*- coding: utf-8 -*-
"""
pos_stock_picking.py
Hooks into POS stock picking validation to create Anglo-Saxon
delivery valuation entries (DR 121200 / CR 110100).
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class StockPickingPos(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        For POS outgoing pickings, button_validate is called internally.
        The parent class (stock_picking.py) already handles this,
        but POS may use _action_done() directly, bypassing button_validate.
        So we also hook _action_done().
        """
        res = super().button_validate()
        return res

    def _action_done(self):
        """
        POS validates stock moves via _action_done(), not button_validate().
        Hook here to catch POS deliveries.
        """
        res = super()._action_done()
        for picking in self:
            if picking.state != 'done':
                continue
            if picking.picking_type_code == 'outgoing' \
                    and not picking.delivery_journal_entry_ids:
                try:
                    picking._create_delivery_valuation_entry()
                    _logger.info(
                        "Anglo-Saxon POS: Delivery valuation created "
                        "for picking '%s'", picking.name
                    )
                except Exception as e:
                    _logger.error(
                        "Anglo-Saxon POS: Failed for picking '%s': %s",
                        picking.name, str(e), exc_info=True
                    )
        return res