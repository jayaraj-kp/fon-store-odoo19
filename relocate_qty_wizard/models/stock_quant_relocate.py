# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockQuantRelocate(models.TransientModel):
    _inherit = 'stock.quant.relocate'

    line_ids = fields.One2many(
        'stock.quant.relocate.line', 'wizard_id', string='Products'
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        # Extract quant ids from context (set by the Relocate button)
        quant_ids = self.env.context.get('active_ids') or []
        if not quant_ids:
            # fallback: parse from defaults['quant_ids'] ORM commands
            raw = defaults.get('quant_ids') or []
            for cmd in raw:
                if isinstance(cmd, (list, tuple)) and len(cmd) >= 3:
                    quant_ids = cmd[2]
                    break
        quants = self.env['stock.quant'].browse(quant_ids)
        lines = []
        for quant in quants:
            lines.append((0, 0, {
                'quant_id': quant.id,
                'qty': quant.quantity,
            }))
        defaults['line_ids'] = lines
        return defaults

    def action_relocate_quants(self):
        """
        Override to use adjusted quantities from line_ids.
        Uses stock.quant._update_available_quantity to move stock
        without manually creating stock.move (avoids field name issues).
        """
        self.ensure_one()
        if not self.dest_location_id:
            raise UserError(_('Please select a destination location.'))

        lines_with_quant = self.line_ids.filtered(lambda l: l.quant_id)
        if not lines_with_quant:
            # No custom lines — fall back to standard behaviour
            return super().action_relocate_quants()

        StockQuant = self.env['stock.quant']

        for line in lines_with_quant:
            quant = line.quant_id
            qty = line.qty

            # Remove qty from source location
            StockQuant._update_available_quantity(
                quant.product_id,
                quant.location_id,
                -qty,
                lot_id=quant.lot_id or None,
                package_id=quant.package_id or None,
                owner_id=quant.owner_id or None,
            )
            # Add qty to destination location
            StockQuant._update_available_quantity(
                quant.product_id,
                self.dest_location_id,
                qty,
                lot_id=quant.lot_id or None,
                package_id=quant.package_id or None,
                owner_id=quant.owner_id or None,
            )

        return {'type': 'ir.actions.act_window_close'}
