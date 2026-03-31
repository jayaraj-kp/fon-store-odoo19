from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    auto_manufacture_mo_ids = fields.Many2many(
        'mrp.production',
        string='Auto-Created Manufacturing Orders',
        copy=False,
    )
    auto_manufacture_count = fields.Integer(
        compute='_compute_auto_manufacture_count',
        string='Auto MO Count',
    )

    @api.depends('auto_manufacture_mo_ids')
    def _compute_auto_manufacture_count(self):
        for order in self:
            order.auto_manufacture_count = len(order.auto_manufacture_mo_ids)

    def action_confirm(self):
        """Override sale order confirmation to trigger auto manufacturing."""
        result = super().action_confirm()

        # Check if auto-manufacture is enabled in settings
        auto_manufacture = self.env['ir.config_parameter'].sudo().get_param(
            'sale_auto_manufacture.auto_manufacture_on_confirm', default='False'
        )

        if auto_manufacture == 'True':
            for order in self:
                order._auto_create_and_produce_manufacturing_orders()

        return result

    def _auto_create_and_produce_manufacturing_orders(self):
        """
        For each sale order line with a product that has a BoM:
        1. Create a Manufacturing Order
        2. Confirm it
        3. Auto-produce it (consume components, add finished goods)
        """
        MrpProduction = self.env['mrp.production']
        created_mos = self.env['mrp.production']

        for line in self.order_line:
            product = line.product_id
            qty = line.product_uom_qty
            uom = line.product_uom

            if not product or qty <= 0:
                continue

            # Find Bill of Materials for this product
            bom = self.env['mrp.bom']._bom_find(
                product,
                company_id=self.company_id.id,
                bom_type='normal',
            )

            # _bom_find returns a dict {product: bom} in Odoo 16+
            # Handle both old and new API signatures
            if isinstance(bom, dict):
                bom = bom.get(product, self.env['mrp.bom'])

            if not bom:
                _logger.info(
                    'No BoM found for product %s, skipping auto-manufacture.',
                    product.display_name
                )
                continue

            _logger.info(
                'Auto-manufacturing %s x %s for sale order %s',
                qty, product.display_name, self.name
            )

            # Convert quantity to BoM UoM if needed
            product_qty = uom._compute_quantity(qty, bom.product_uom_id)

            # Create Manufacturing Order
            mo_vals = {
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom_id': bom.product_uom_id.id,
                'bom_id': bom.id,
                'company_id': self.company_id.id,
                'origin': self.name,
                'sale_order_id': self.id if 'sale_order_id' in MrpProduction._fields else False,
            }

            # Remove sale_order_id if field doesn't exist (avoid error)
            if 'sale_order_id' not in MrpProduction._fields:
                mo_vals.pop('sale_order_id', None)

            mo = MrpProduction.create(mo_vals)
            created_mos |= mo

            # Confirm the Manufacturing Order
            mo.action_confirm()

            # Check & reserve component availability
            mo.action_assign()

            # Auto-produce: set qty_producing and finish
            self._auto_produce_mo(mo, product_qty)

        if created_mos:
            self.auto_manufacture_mo_ids = [(4, mo.id) for mo in created_mos]
            _logger.info(
                'Auto-manufactured %d MO(s) for sale order %s',
                len(created_mos), self.name
            )

    def _auto_produce_mo(self, mo, qty_to_produce):
        """
        Mark manufacturing order as fully produced.
        This consumes components and adds finished product to stock.
        """
        try:
            # Set quantity being produced
            mo.qty_producing = qty_to_produce

            # Fill in the component quantities (immediate transfer approach)
            for move in mo.move_raw_ids:
                if move.state not in ('done', 'cancel'):
                    # Set the done quantity on move lines
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.reserved_qty or move_line.quantity
                    # If no move lines exist, create them
                    if not move.move_line_ids:
                        move.quantity = move.product_uom_qty

            # Set finished product done quantity
            for move in mo.move_finished_ids:
                if move.state not in ('done', 'cancel'):
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move_line.reserved_qty or move_line.quantity
                    if not move.move_line_ids:
                        move.quantity = move.product_uom_qty

            # Mark as done / produce
            if hasattr(mo, 'button_mark_done'):
                mo.button_mark_done()
            elif hasattr(mo, '_action_mark_done'):
                mo._action_mark_done()

            _logger.info('MO %s auto-produced successfully.', mo.name)

        except Exception as e:
            _logger.warning(
                'Auto-produce failed for MO %s: %s. '
                'MO is confirmed but needs manual production.',
                mo.name, str(e)
            )
            # Don't raise — MO is created & confirmed, just needs manual finish

    def action_view_auto_manufacture_orders(self):
        """Smart button to view auto-created MOs from this sale order."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Manufacturing Orders'),
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.auto_manufacture_mo_ids.ids)],
            'context': {'default_origin': self.name},
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    has_bom = fields.Boolean(
        compute='_compute_has_bom',
        string='Has Bill of Materials',
        help='Indicates if this product has a BoM and will be auto-manufactured',
    )

    @api.depends('product_id')
    def _compute_has_bom(self):
        for line in self:
            if line.product_id:
                bom = self.env['mrp.bom']._bom_find(
                    line.product_id,
                    company_id=line.company_id.id,
                    bom_type='normal',
                )
                if isinstance(bom, dict):
                    bom = bom.get(line.product_id, self.env['mrp.bom'])
                line.has_bom = bool(bom)
            else:
                line.has_bom = False
