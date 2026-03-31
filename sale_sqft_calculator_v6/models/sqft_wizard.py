from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SqftCalculatorWizard(models.TransientModel):
    _name = 'sqft.calculator.wizard'
    _description = 'Square Feet Calculator Wizard'

    sale_order_line_id = fields.Many2one(
        'sale.order.line',
        string='Order Line',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        related='sale_order_line_id.product_id',
        string='Product',
        readonly=True,
    )
    width = fields.Float(
        string='Width (ft)',
        digits=(16, 4),
        required=True,
        default=0.0,
    )
    height = fields.Float(
        string='Height (ft)',
        digits=(16, 4),
        required=True,
        default=0.0,
    )
    sqft = fields.Float(
        string='Square Feet',
        digits=(16, 4),
        compute='_compute_sqft',
    )
    sqft_display = fields.Char(
        string='Calculated Area',
        compute='_compute_sqft',
    )

    @api.depends('width', 'height')
    def _compute_sqft(self):
        for wizard in self:
            area = wizard.width * wizard.height
            wizard.sqft = area
            wizard.sqft_display = f"{area:.4f} sq.ft"

    @api.constrains('width', 'height')
    def _check_positive_values(self):
        for wizard in self:
            if wizard.width < 0 or wizard.height < 0:
                raise ValidationError("Width and Height must be positive values!")

    def action_apply(self):
        """Apply the calculated sqft to the order line quantity."""
        self.ensure_one()
        if self.sqft <= 0:
            raise ValidationError(
                "Please enter valid Width and Height values greater than 0."
            )
        self.sale_order_line_id.write({
            'width': self.width,
            'height': self.height,
            'product_uom_qty': self.sqft,
            'is_sqft_product': True,
        })
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Close wizard without applying."""
        return {'type': 'ir.actions.act_window_close'}
