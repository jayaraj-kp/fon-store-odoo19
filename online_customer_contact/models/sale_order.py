from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

ONLINE_PARENT_XMLID = 'online_customer_contact.partner_online_customers'

SYNC_FIELDS = {
    'partner_id',
    'online_customer_name',
    'online_customer_phone',
    'online_customer_street',
    'online_customer_city',
    'online_customer_zip',
    'online_customer_state_id',
    'online_customer_country_id',
}


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_online_customer = fields.Boolean(
        compute='_compute_is_online_customer',
        help="Technical field: True when the customer is the Online Customers parent.",
    )
    online_customer_name = fields.Char(string="Name")
    online_customer_phone = fields.Char(string="Phone")
    online_customer_street = fields.Char(string="Street")
    online_customer_city = fields.Char(string="City")
    online_customer_zip = fields.Char(string="Zip")
    online_customer_state_id = fields.Many2one(
        'res.country.state',
        string="State",
        domain="[('country_id', '=?', online_customer_country_id)]",
    )
    online_customer_country_id = fields.Many2one('res.country', string="Country")
    online_contact_id = fields.Many2one(
        'res.partner',
        string="Online Contact",
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_online_parent(self):
        return self.env.ref(ONLINE_PARENT_XMLID, raise_if_not_found=False)

    @api.depends('partner_id')
    def _compute_is_online_customer(self):
        parent = self._get_online_parent()
        for order in self:
            order.is_online_customer = bool(
                parent and order.partner_id and order.partner_id.id == parent.id
            )

    def _prepare_online_contact_vals(self, parent):
        self.ensure_one()
        return {
            'name': (self.online_customer_name or '').strip(),
            'phone': (self.online_customer_phone or '').strip() or False,
            'street': self.online_customer_street or False,
            'city': self.online_customer_city or False,
            'zip': self.online_customer_zip or False,
            'state_id': self.online_customer_state_id.id or False,
            'country_id': self.online_customer_country_id.id or False,
            'parent_id': parent.id,
            'type': 'contact',
        }

    def _sync_online_contact(self):
        """Create (or reuse) a child contact under the Online Customers parent."""
        parent = self._get_online_parent()
        if not parent:
            return
        Partner = self.env['res.partner']
        for order in self:
            if order.partner_id != parent:
                continue
            name = (order.online_customer_name or '').strip()
            if not name:
                continue

            vals = order._prepare_online_contact_vals(parent)
            contact = Partner.search([
                ('parent_id', '=', parent.id),
                ('name', '=', vals['name']),
                ('phone', '=', vals['phone']),
            ], limit=1)

            if contact:
                address_vals = {}
                for key in ('street', 'city', 'zip'):
                    if (contact[key] or False) != vals[key]:
                        address_vals[key] = vals[key]
                for key in ('state_id', 'country_id'):
                    if contact[key].id != vals[key]:
                        address_vals[key] = vals[key]
                if address_vals:
                    contact.write(address_vals)
            else:
                contact = Partner.create(vals)

            order.with_context(skip_online_sync=True).write({
                'online_contact_id': contact.id,
                'partner_invoice_id': contact.id,
                'partner_shipping_id': contact.id,
            })

    # ------------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_online_contact()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_online_sync') and SYNC_FIELDS & set(vals):
            self._sync_online_contact()
        return res

    def action_confirm(self):
        for order in self.filtered('is_online_customer'):
            if not order.online_customer_name or not order.online_customer_phone:
                raise ValidationError(_(
                    "Please enter the online customer's name and phone "
                    "in the 'Online Customer' tab before confirming."
                ))
        return super().action_confirm()
