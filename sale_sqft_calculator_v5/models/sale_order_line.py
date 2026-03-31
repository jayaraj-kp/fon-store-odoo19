from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    width = fields.Float(
        string='Width (ft)',
        digits=(16, 4),
        default=0.0,
    )
    height = fields.Float(
        string='Height (ft)',
        digits=(16, 4),
        default=0.0,
    )
    sqft = fields.Float(
        string='Sq. Ft.',
        digits=(16, 4),
        compute='_compute_sqft',
        store=True,
    )
    is_sqft_product = fields.Boolean(
        string='Uses Sq.Ft.',
        default=False,
    )

    @api.depends('width', 'height')
    def _compute_sqft(self):
        for line in self:
            line.sqft = line.width * line.height

    @api.onchange('sqft')
    def _onchange_sqft_update_qty(self):
        """Automatically update quantity when sqft changes."""
        for line in self:
            if line.is_sqft_product and line.sqft > 0:
                line.product_uom_qty = line.sqft

    def action_open_sqft_wizard(self):
        """Open the width/height popup wizard."""
        self.ensure_one()
        wizard = self.env['sqft.calculator.wizard'].create({
            'sale_order_line_id': self.id,
            'width': self.width,
            'height': self.height,
        })
        return {
            'name': 'Square Feet Calculator',
            'type': 'ir.actions.act_window',
            'res_model': 'sqft.calculator.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }
