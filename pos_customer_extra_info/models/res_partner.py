from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_pos_extra_info(self):
        """Return extra info for POS customer list."""
        result = {}
        for partner in self:
            # Get last invoice
            last_invoice = self.env['account.move'].search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
            ], order='invoice_date desc, id desc', limit=1)

            # Count all posted invoices
            invoice_count = self.env['account.move'].search_count([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
            ])

            # Tags
            tags = partner.category_id.mapped('name')

            result[partner.id] = {
                'last_invoice_name': last_invoice.name if last_invoice else '',
                'last_invoice_date': last_invoice.invoice_date.strftime('%Y-%m-%d') if last_invoice and last_invoice.invoice_date else '',
                'invoice_count': invoice_count,
                'tags': ', '.join(tags) if tags else '',
            }
        return result

    @api.model
    def get_pos_extra_info(self, partner_ids):
        partners = self.browse(partner_ids)
        return partners._get_pos_extra_info()
