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
        # quant_ids is set by the standard wizard via context
        quant_ids = defaults.get('quant_ids') or []
        # quant_ids may come as ORM command list [(6,0,[ids])] or plain list
        if quant_ids and isinstance(quant_ids[0], (list, tuple)):
            quant_ids = quant_ids[0][2]
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

        StockMove = self.env['stock.move']

        for line in self.line_ids:
            quant = line.quant_id
            move = StockMove.create({
                'name': self.message or _('Product Relocated'),
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
            })
            move._action_confirm()
            move._action_assign()
            move._action_done()

        return {'type': 'ir.actions.act_window_close'}
