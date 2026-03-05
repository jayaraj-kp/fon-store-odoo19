# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = 'pos.config'

    # ── Shop Code ────────────────────────────────────────────────────────────
    shop_code = fields.Char(
        string='Customer ID Prefix',
        size=10,
        help=(
            "Short prefix code used for auto-generating customer IDs.\n"
            "Example: Enter 'CHL' for Chelari → customers get IDs like CHL - 00001\n"
            "Example: Enter 'KON' for Kondotty → customers get IDs like KON - 00001"
        ),
    )
    customer_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='Customer ID Sequence',
        readonly=True,
        copy=False,
        ondelete='set null',
        help="Auto-created sequence used to generate unique customer IDs for this shop.",
    )
    customer_id_count = fields.Integer(
        string='Customers Created',
        compute='_compute_customer_id_count',
        help="Total customers created from this shop.",
    )

    # ── Compute ──────────────────────────────────────────────────────────────
    def _compute_customer_id_count(self):
        for config in self:
            config.customer_id_count = self.env['res.partner'].search_count([
                ('pos_config_id', '=', config.id)
            ])

    # ── ORM Overrides ────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.shop_code:
                record._sync_customer_sequence()
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'shop_code' in vals:
            for config in self:
                config._sync_customer_sequence()
        return result

    # ── Sequence Management ──────────────────────────────────────────────────
    def _sync_customer_sequence(self):
        """Create or update the ir.sequence for this shop's customer IDs."""
        self.ensure_one()
        if not self.shop_code:
            return

        code = self.shop_code.upper().strip()
        prefix = f'{code} - '
        seq_name = f'POS Customer ID [{self.name}]'
        seq_code = f'pos.customer.uid.{self.id}'

        if self.customer_sequence_id:
            # Update existing sequence prefix in case shop_code changed
            self.customer_sequence_id.sudo().write({
                'name': seq_name,
                'prefix': prefix,
            })
        else:
            # Create a brand-new sequence for this shop
            seq = self.env['ir.sequence'].sudo().create({
                'name': seq_name,
                'code': seq_code,
                'prefix': prefix,
                'padding': 5,          # Gives: 00001, 00002 …
                'number_increment': 1,
                'number_next': 1,
                'implementation': 'no_gap',  # True sequential, no gaps
                'company_id': self.company_id.id if self.company_id else False,
            })
            self.sudo().write({'customer_sequence_id': seq.id})

    def _get_next_customer_id(self):
        """Return the next formatted customer ID string for this shop."""
        self.ensure_one()
        if not self.shop_code:
            return False
        if not self.customer_sequence_id:
            self._sync_customer_sequence()
        if self.customer_sequence_id:
            return self.customer_sequence_id.next_by_id()
        return False

    # ── Action Buttons (Backend UI) ──────────────────────────────────────────
    def action_setup_customer_sequence(self):
        """Manually (re)create the customer ID sequence for this shop."""
        self.ensure_one()
        if not self.shop_code:
            raise UserError(_(
                "Please enter a Shop Code / Customer ID Prefix first before setting up the sequence."
            ))
        self._sync_customer_sequence()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sequence Ready'),
                'message': _(
                    'Customer ID sequence is set up for %(shop)s. '
                    'New customers will be assigned IDs starting with %(prefix)s - 00001.',
                    shop=self.name,
                    prefix=self.shop_code.upper(),
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_reset_customer_sequence(self):
        """Reset the sequence counter back to 1 (use with caution!)."""
        self.ensure_one()
        if not self.customer_sequence_id:
            raise UserError(_("No sequence found for this shop. Set a Shop Code first."))
        self.customer_sequence_id.sudo().write({'number_next': 1})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sequence Reset'),
                'message': _('Customer ID counter reset to 1 for %s.') % self.name,
                'type': 'warning',
                'sticky': False,
            }
        }

    def action_view_shop_customers(self):
        """Open list of customers created from this shop."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customers – %s') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('pos_config_id', '=', self.id)],
            'context': {'default_pos_config_id': self.id},
        }
