# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ScrapBulkEntry(models.Model):
    _name = 'scrap.bulk.entry'
    _description = 'Scrap Bulk Entry'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True, copy=False)

    location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain=[('usage', 'in', ['internal', 'transit'])],
        states={'done': [('readonly', True)]},
    )
    scrap_location_id = fields.Many2one(
        'stock.location',
        string='Scrap Location',
        required=True,
        domain=[('scrap_location', '=', True)],
        states={'done': [('readonly', True)]},
        default=lambda self: self.env['stock.location'].search(
            [('scrap_location', '=', True)], limit=1
        ),
    )
    scrap_reason = fields.Char(
        string='Scrap Reason',
        states={'done': [('readonly', True)]},
    )
    scrap_date = fields.Datetime(
        string='Scrap Date',
        default=fields.Datetime.now,
        states={'done': [('readonly', True)]},
    )
    note = fields.Text(
        string='Notes',
        states={'done': [('readonly', True)]},
    )
    scrap_line_ids = fields.One2many(
        'scrap.bulk.entry.line',
        'bulk_entry_id',
        string='Scrap Lines',
        states={'done': [('readonly', True)]},
    )
    scrap_ids = fields.Many2many(
        'stock.scrap',
        string='Scrap Orders',
        copy=False,
    )
    scrap_count = fields.Integer(
        string='Scrap Orders Count',
        compute='_compute_scrap_count',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'scrap.bulk.entry'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('scrap_ids')
    def _compute_scrap_count(self):
        for rec in self:
            rec.scrap_count = len(rec.scrap_ids)

    def action_validate(self):
        """Validate the bulk scrap entry and create individual scrap orders."""
        self.ensure_one()
        if not self.scrap_line_ids:
            raise UserError(_('Please add at least one scrap line before validating.'))

        for line in self.scrap_line_ids:
            if not line.product_id:
                raise UserError(_('All scrap lines must have a product selected.'))
            if line.quantity <= 0:
                raise UserError(_('Quantity must be greater than zero for all lines.'))

        # Detect correct field names for stock.scrap in this Odoo version
        scrap_model_fields = self.env['stock.scrap']._fields
        qty_field = 'scrap_qty' if 'scrap_qty' in scrap_model_fields else 'quantity'
        uom_field = 'product_uom_id' if 'product_uom_id' in scrap_model_fields else 'product_uom_id'

        scrap_orders = self.env['stock.scrap']
        for line in self.scrap_line_ids:
            source_location = line.location_id or self.location_id
            scrap_vals = {
                'product_id': line.product_id.id,
                uom_field: line.product_uom_id.id,
                qty_field: line.quantity,
                'scrap_location_id': self.scrap_location_id.id,
                'company_id': self.company_id.id,
            }
            if source_location:
                scrap_vals['location_id'] = source_location.id

            scrap_order = self.env['stock.scrap'].create(scrap_vals)
            scrap_order.action_validate()
            scrap_orders |= scrap_order

        self.write({
            'scrap_ids': [(6, 0, scrap_orders.ids)],
            'state': 'done',
        })

    def action_view_scraps(self):
        """Open the related scrap orders."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_stock_scrap')
        if self.scrap_count == 1:
            action['res_id'] = self.scrap_ids[0].id
            action['view_mode'] = 'form'
            action['views'] = [(False, 'form')]
        else:
            action['domain'] = [('id', 'in', self.scrap_ids.ids)]
        return action

    def action_set_draft(self):
        """Reset to draft (only if no scrap orders created)."""
        for rec in self:
            if rec.scrap_ids:
                raise UserError(_(
                    'Cannot reset to draft: scrap orders have already been created.'
                ))
            rec.state = 'draft'
