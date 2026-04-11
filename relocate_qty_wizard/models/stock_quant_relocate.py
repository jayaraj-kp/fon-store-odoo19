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
        Override to relocate using adjusted quantities from line_ids.

        Strategy: temporarily set each quant's quantity to the user-specified
        qty, call super() (which handles moves + accounting properly), then
        the quant is consumed by Odoo's own logic.

        If no custom lines exist, fall back to standard behaviour entirely.
        """
        self.ensure_one()

        lines_with_quant = self.line_ids.filtered(lambda l: l.quant_id)
        if not lines_with_quant:
            return super().action_relocate_quants()

        # Validate quantities before doing anything
        for line in lines_with_quant:
            if line.qty <= 0:
                raise UserError(
                    _('Quantity must be greater than zero for "%s".')
                    % line.product_id.display_name
                )
            if line.qty > line.quant_id.quantity:
                raise UserError(_(
                    'Qty to relocate (%(qty)s) exceeds on-hand (%(avail)s) for "%(product)s".',
                    qty=line.qty,
                    avail=line.quant_id.quantity,
                    product=line.product_id.display_name,
                ))

        # For each line where qty < full quant qty:
        # Split the quant so super() only sees the portion to move.
        original_quant_ids = self.quant_ids.ids
        quants_to_restore = []  # (quant, original_qty)

        for line in lines_with_quant:
            quant = line.quant_id
            original_qty = quant.quantity
            if line.qty < original_qty:
                # Temporarily reduce quant to the requested qty.
                # super() will relocate exactly this quant.
                quant.sudo().write({'quantity': line.qty})
                quants_to_restore.append((quant, original_qty, line.qty))

        try:
            result = super().action_relocate_quants()
        except Exception:
            # Restore quantities on failure
            for quant, orig_qty, _ in quants_to_restore:
                quant.sudo().write({'quantity': orig_qty})
            raise

        # After super() the quant at source has been reduced by line.qty
        # (Odoo moved it). Restore remainder at source if we reduced it.
        for quant, orig_qty, moved_qty in quants_to_restore:
            remainder = orig_qty - moved_qty
            if remainder > 0:
                self.env['stock.quant']._update_available_quantity(
                    quant.product_id,
                    quant.location_id,
                    remainder,
                    lot_id=quant.lot_id or None,
                    package_id=quant.package_id or None,
                    owner_id=quant.owner_id or None,
                )

        return result
