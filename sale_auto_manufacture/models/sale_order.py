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
            uom = (
                line.product_uom_id
                if hasattr(line, 'product_uom_id') and line.product_uom_id
                else getattr(line, 'product_uom', None) or product.uom_id
            )

            if not product or qty <= 0:
                continue

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

            mo = MrpProduction.create({
                'product_id': product.id,
                'product_qty': product_qty,
                'product_uom_id': bom.product_uom_id.id,
                'bom_id': bom.id,
                'company_id': self.company_id.id,
                'origin': self.name,
            })
            created_mos |= mo

            # Confirm the MO
            mo.action_confirm()

            # Try to reserve stock
            mo.action_assign()

            # Produce fully
            self._auto_produce_mo(mo, product_qty)

        if created_mos:
            self.auto_manufacture_mo_ids = [(4, mo.id) for mo in created_mos]

    def _auto_produce_mo(self, mo, qty_to_produce):
        """
        Fully produce an MO in Odoo 19, simulating:
          Produce All → Set Quantities → Validate
        
        Odoo 19 specifics confirmed from DB inspection:
          - stock_move_line uses 'quantity' field (not qty_done)
          - stock_move_line has 'picked' boolean → must be True
          - stock_move has 'picked' boolean → must be True
          - button_mark_done() returns wizard when state='to_close'
          - Must use context skip_immediate=True, skip_backorder=True
            to bypass all wizard popups and go straight to Done
        """
        try:
            # Step 1: Set qty_producing on MO (simulates "Produce All")
            mo.qty_producing = qty_to_produce

            # Step 2: Process RAW MATERIAL (component) moves
            # Simulates "Set Quantities" on each component
            for move in mo.move_raw_ids:
                if move.state in ('done', 'cancel'):
                    continue

                needed_qty = move.product_uom_qty

                if move.move_line_ids:
                    # Move lines exist (stock was reserved via action_assign)
                    for ml in move.move_line_ids:
                        ml.quantity = ml.reserved_uom_qty or needed_qty
                        ml.picked = True
                else:
                    # No move lines — set directly on the move
                    # This handles cases where stock reservation created no lines
                    move.write({
                        'quantity': needed_qty,
                        'picked': True,
                    })

            # Step 3: Process FINISHED PRODUCT moves
            for move in mo.move_finished_ids:
                if move.state in ('done', 'cancel'):
                    continue

                needed_qty = move.product_uom_qty

                if move.move_line_ids:
                    for ml in move.move_line_ids:
                        ml.quantity = ml.reserved_uom_qty or needed_qty
                        ml.picked = True
                else:
                    move.write({
                        'quantity': needed_qty,
                        'picked': True,
                    })

            # Step 4: Validate — simulates clicking "Validate"
            # Use context to bypass ALL wizard popups:
            #   skip_immediate   → skips "Set Quantities" wizard
            #   skip_backorder   → skips backorder creation wizard
            mo_ctx = mo.with_context(
                skip_immediate=True,
                skip_backorder=True,
                no_recompute=True,
            )

            result = mo_ctx.button_mark_done()

            # If still returned a wizard action, force via _action_mark_done
            if isinstance(result, dict) and result.get('type') == 'ir.actions.act_window':
                _logger.info(
                    'MO %s: wizard returned, forcing _action_mark_done.', mo.name
                )
                mo_ctx._action_mark_done()

            _logger.info(
                'MO %s auto-produced successfully. Final state: %s',
                mo.name, mo.state
            )

        except Exception as e:
            _logger.warning(
                'Auto-produce failed for MO %s: %s. Needs manual production.',
                mo.name, str(e),
                exc_info=True,
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
