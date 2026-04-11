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
        Override to use the adjusted quantities from line_ids
        instead of the original quant quantities.
        """
        self.ensure_one()
        if not self.dest_location_id:
            raise UserError(_('Please select a destination location.'))

        lines_with_quant = self.line_ids.filtered(lambda l: l.quant_id)
        if not lines_with_quant:
            # No lines with quant — fall back to standard behaviour
            return super().action_relocate_quants()

        StockMove = self.env['stock.move']
        move_note = getattr(self, 'message', None) or _('Product Relocated')

        for line in lines_with_quant:
            quant = line.quant_id
            StockMove.create({
                'name': move_note,
                'product_id': quant.product_id.id,
                'product_uom': quant.product_uom_id.id,
                'product_uom_qty': line.qty,
                'location_id': quant.location_id.id,
                'location_dest_id': self.dest_location_id.id,
                'state': 'draft',
                'move_line_ids': [(0, 0, {
                    'product_id': quant.product_id.id,
                    'product_uom_id': quant.product_uom_id.id,
                    'qty_done': line.qty,
                    'location_id': quant.location_id.id,
                    'location_dest_id': self.dest_location_id.id,
                    'lot_id': quant.lot_id.id if quant.lot_id else False,
                    'package_id': quant.package_id.id if quant.package_id else False,
                    'owner_id': quant.owner_id.id if quant.owner_id else False,
                })],
            })._action_confirm()._action_assign()._action_done()

        return {'type': 'ir.actions.act_window_close'}
