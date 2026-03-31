from odoo import models, fields, api, _
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

        auto_manufacture = self.env['ir.config_parameter'].sudo().get_param(
            'sale_auto_manufacture.auto_manufacture_on_confirm', default='False'
        )

        if auto_manufacture == 'True':
            for order in self:
                order._auto_create_and_produce_manufacturing_orders()

        return result

    def _auto_create_and_produce_manufacturing_orders(self):
        MrpProduction = self.env['mrp.production']
        created_mos = self.env['mrp.production']

        for line in self.order_line:
            product = line.product_id
            qty = line.product_uom_qty

            # Odoo 17+ renamed product_uom -> product_uom_id on sale.order.line
            uom = (
                line.product_uom_id
                if hasattr(line, 'product_uom_id') and line.product_uom_id
                else getattr(line, 'product_uom', None) or product.uom_id
            )

            if not product or qty <= 0:
                continue

            # Find Bill of Materials
            bom = self.env['mrp.bom']._bom_find(
                product,
                company_id=self.company_id.id,
                bom_type='normal',
            )
            if isinstance(bom, dict):
                bom = bom.get(product, self.env['mrp.bom'])

            if not bom:
                _logger.info('No BoM for %s, skipping.', product.display_name)
                continue

            product_qty = uom._compute_quantity(qty, bom.product_uom_id)

            mo_vals = {
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom_id': bom.product_uom_id.id,
                'bom_id': bom.id,
                'company_id': self.company_id.id,
                'origin': self.name,
            }

            mo = MrpProduction.create(mo_vals)
            created_mos |= mo

            mo.action_confirm()
            mo.action_assign()
            self._auto_produce_mo(mo, product_qty)

        if created_mos:
            self.auto_manufacture_mo_ids = [(4, mo.id) for mo in created_mos]

    def _auto_produce_mo(self, mo, qty_to_produce):
        """
        Fully produce an MO in Odoo 19:
        1. Set qty_producing
        2. Set consumed quantities on move lines
        3. Call button_mark_done to go from 'To Close' -> 'Done'
           If it returns a wizard action, bypass it with immediate_transfer
        """
        try:
            mo.qty_producing = qty_to_produce

            # Set done quantities on raw material (component) moves
            for move in mo.move_raw_ids:
                if move.state in ('done', 'cancel'):
                    continue
                if move.move_line_ids:
                    for ml in move.move_line_ids:
                        if hasattr(ml, 'quantity'):
                            ml.quantity = ml.reserved_uom_qty or ml.product_uom_qty
                        else:
                            ml.qty_done = ml.product_uom_qty
                else:
                    move.quantity = move.product_uom_qty

            # Set done quantities on finished product moves
            for move in mo.move_finished_ids:
                if move.state in ('done', 'cancel'):
                    continue
                if move.move_line_ids:
                    for ml in move.move_line_ids:
                        if hasattr(ml, 'quantity'):
                            ml.quantity = ml.reserved_uom_qty or ml.product_uom_qty
                        else:
                            ml.qty_done = ml.product_uom_qty
                else:
                    move.quantity = move.product_uom_qty

            # In Odoo 19, button_mark_done may return a wizard action
            # when state is 'to_close'. We detect this and call _action_mark_done
            # directly to skip the wizard and finalize immediately.
            result = None
            if hasattr(mo, 'button_mark_done'):
                result = mo.button_mark_done()

            # If a wizard/action was returned instead of completing, force finish
            if isinstance(result, dict) and result.get('type') in (
                'ir.actions.act_window',
                'ir.actions.act_window_close',
            ):
                _logger.info(
                    'MO %s returned wizard on button_mark_done, '
                    'forcing _action_mark_done directly.', mo.name
                )
                if hasattr(mo, '_action_mark_done'):
                    mo._action_mark_done()
                elif mo.state == 'to_close':
                    # Last resort: write state directly via stock moves
                    mo.move_raw_ids.filtered(
                        lambda m: m.state not in ('done', 'cancel')
                    )._action_done()
                    mo.move_finished_ids.filtered(
                        lambda m: m.state not in ('done', 'cancel')
                    )._action_done()
                    mo.write({'state': 'done'})

            _logger.info('MO %s completed. State: %s', mo.name, mo.state)

        except Exception as e:
            _logger.warning(
                'Auto-produce failed for MO %s: %s. '
                'MO needs manual production.', mo.name, str(e)
            )

    def action_view_auto_manufacture_orders(self):
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
