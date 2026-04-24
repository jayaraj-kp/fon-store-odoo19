# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockLocationGenerateWizard(models.TransientModel):
    _name = 'stock.location.generate.wizard'
    _description = 'Generate Rack / Box Locations Wizard'

    # ── Creation type ────────────────────────────────────────────────────────
    create_type = fields.Selection(
        selection=[('rack', 'Rack'), ('box', 'Box')],
        string='Create',
        default='rack',
        required=True,
    )

    # ── Naming ───────────────────────────────────────────────────────────────
    prefix = fields.Char(
        string='Prefix',
        help='Optional text placed before the number (e.g. "R-" → R-1, R-2 …). '
             'Leave blank to use the location type as prefix.',
    )

    from_number = fields.Integer(string='From', default=1, required=True)
    to_number   = fields.Integer(string='To',   default=10, required=True)

    # ── Target location ──────────────────────────────────────────────────────
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        help='Warehouse that owns the parent location.',
    )

    location_id = fields.Many2one(
        'stock.location',
        string='In',
        required=True,
        domain=[('usage', 'in', ['internal', 'view'])],
        help='Parent location where new sub-locations will be created.',
    )

    # ── Auto-fill warehouse when location changes ─────────────────────────────
    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            # Try to find the warehouse whose lot_stock_id matches
            warehouse = self.env['stock.warehouse'].search(
                [('lot_stock_id', '=', self.location_id.id)], limit=1
            )
            if not warehouse:
                # Walk up the location hierarchy
                loc = self.location_id
                while loc and not warehouse:
                    warehouse = self.env['stock.warehouse'].search(
                        [('view_location_id', '=', loc.id)], limit=1
                    )
                    loc = loc.location_id
            if warehouse:
                self.warehouse_id = warehouse

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id and not self.location_id:
            self.location_id = self.warehouse_id.lot_stock_id

    # ── Validation ───────────────────────────────────────────────────────────
    @api.constrains('from_number', 'to_number')
    def _check_range(self):
        for rec in self:
            if rec.from_number < 1:
                raise ValidationError(_('From must be greater than or equal to 1.'))
            if rec.to_number < rec.from_number:
                raise ValidationError(_('"To" must be greater than or equal to "From".'))
            if (rec.to_number - rec.from_number) > 999:
                raise ValidationError(_('You cannot generate more than 1 000 locations at once.'))

    # ── Core action ──────────────────────────────────────────────────────────
    # ── Core action ──────────────────────────────────────────────────────────
    def action_generate(self):
        self.ensure_one()

        # Determine the effective prefix
        if self.prefix:
            # Ensure there's always a space between prefix and number
            label_prefix = self.prefix.rstrip() + ' '
        else:
            label_prefix = 'Rack ' if self.create_type == 'rack' else 'BOX '

        parent_location = self.location_id
        created = self.env['stock.location']
        skipped = []

        for number in range(self.from_number, self.to_number + 1):
            name = f"{label_prefix}{number}"

            # Skip duplicates that already exist under the same parent
            existing = self.env['stock.location'].search([
                ('name', '=', name),
                ('location_id', '=', parent_location.id),
            ], limit=1)

            if existing:
                skipped.append(name)
                continue

            created |= self.env['stock.location'].create({
                'name': name,
                'location_id': parent_location.id,
                'usage': 'internal',
                'active': True,
            })

        # Build feedback message
        msg_parts = []
        if created:
            msg_parts.append(
                _('%d location(s) created successfully under "%s".')
                % (len(created), parent_location.complete_name)
            )
        if skipped:
            msg_parts.append(
                _('Skipped %d duplicate(s): %s.')
                % (len(skipped), ', '.join(skipped))
            )
        if not created and not skipped:
            msg_parts.append(_('No locations were created.'))

        message = ' '.join(msg_parts)

        # Return a simple notification — no 'next' key (not supported in Odoo 19 CE)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Location Generation Complete'),
                'message': message,
                'type': 'success' if created else 'warning',
                'sticky': False,
            },
        }
