# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class RelocateQtyWizardLine(models.TransientModel):
    """One line per selected quant — user can edit the qty to relocate."""
    _name = 'relocate.qty.wizard.line'
    _description = 'Relocate Wizard Line'

    wizard_id = fields.Many2one('relocate.qty.wizard', required=True, ondelete='cascade')
    quant_id = fields.Many2one('stock.quant', string='Quant', required=True)
    product_id = fields.Many2one(related='quant_id.product_id', string='Product', readonly=True)
    location_id = fields.Many2one(related='quant_id.location_id', string='From Location', readonly=True)
    available_qty = fields.Float(related='quant_id.quantity', string='Available Qty', readonly=True)
    qty = fields.Float(string='Quantity', required=True, digits='Product Unit of Measure')

    @api.constrains('qty', 'available_qty')
    def _check_qty(self):
        for line in self:
            if line.qty <= 0:
                raise UserError(_('Quantity must be greater than zero for product "%s".') % line.product_id.display_name)
            if line.qty > line.available_qty:
                raise UserError(_(
                    'Quantity to relocate (%(qty)s) cannot exceed available quantity (%(avail)s) for product "%(product)s".',
                    qty=line.qty,
                    avail=line.available_qty,
                    product=line.product_id.display_name,
                ))


class RelocateQtyWizard(models.TransientModel):
    _name = 'relocate.qty.wizard'
    _description = 'Relocate Stock Quant with Quantity Adjustment'

    quant_ids = fields.Many2many('stock.quant', string='Quants')
    dest_location_id = fields.Many2one(
        'stock.location', string='Destination Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        required=True,
    )
    reason = fields.Char(string='Reason for Relocate', default='Product Relocated')
    line_ids = fields.One2many('relocate.qty.wizard.line', 'wizard_id', string='Products')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        quant_ids = self.env.context.get('default_quant_ids', [])
        quants = self.env['stock.quant'].browse(quant_ids)
        lines = []
        for quant in quants:
            lines.append((0, 0, {
                'quant_id': quant.id,
                'qty': quant.quantity,  # pre-fill with full available qty
            }))
        defaults['line_ids'] = lines
        return defaults

    def action_confirm(self):
        self.ensure_one()
        if not self.dest_location_id:
            raise UserError(_('Please select a destination location.'))
        if not self.line_ids:
            raise UserError(_('No products to relocate.'))

        StockMove = self.env['stock.move']
        for line in self.line_ids:
            quant = line.quant_id
            move = StockMove.create({
                'name': self.reason or _('Product Relocated'),
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
