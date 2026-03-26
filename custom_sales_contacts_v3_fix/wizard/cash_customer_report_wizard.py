# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CashCustomerReportWizard(models.TransientModel):
    _name = 'cash.customer.report.wizard'
    _description = 'Cash Customer POS Report Wizard'

    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    partner_ids = fields.Many2many(
        'res.partner',
        string='Specific Customers',
        help='Leave empty to include ALL cash customers',
        domain="[('parent_id.name', 'ilike', 'cash customer')]"
    )

    def action_print_report(self):
        data = {
            'date_from': self.date_from and str(self.date_from) or False,
            'date_to': self.date_to and str(self.date_to) or False,
            'partner_ids': self.partner_ids.ids or [],
        }
        return self.env.ref(
            'custom_sales_contacts_v3.action_cash_customer_pos_report'
        ).report_action(self, data=data)


class CashCustomerReportParser(models.AbstractModel):
    _name = 'report.custom_sales_contacts_v3.cash_customer_report_template'
    _description = 'Cash Customer POS Report Parser'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        partner_ids = data.get('partner_ids', [])

        # Get all CASH CUSTOMER child contacts
        domain = [('parent_id.name', 'ilike', 'cash customer')]
        if partner_ids:
            domain.append(('id', 'in', partner_ids))
        partners = self.env['res.partner'].search(domain, order='name asc')

        report_lines = []
        grand_total = 0.0
        grand_orders = 0

        for partner in partners:
            # Build POS order domain for this partner
            pos_domain = [('partner_id', '=', partner.id), ('state', 'in', ['paid', 'done', 'invoiced'])]
            if date_from:
                pos_domain.append(('date_order', '>=', date_from + ' 00:00:00'))
            if date_to:
                pos_domain.append(('date_order', '<=', date_to + ' 23:59:59'))

            pos_orders = self.env['pos.order'].search(pos_domain, order='date_order desc')

            orders_data = []
            partner_total = 0.0
            for order in pos_orders:
                orders_data.append({
                    'name': order.name,
                    'date': order.date_order,
                    'amount_total': order.amount_total,
                    'amount_paid': order.amount_paid,
                    'payment_method': ', '.join(order.payment_ids.mapped('payment_method_id.name')),
                    'state': order.state,
                })
                partner_total += order.amount_total

            grand_total += partner_total
            grand_orders += len(pos_orders)

            # Safely resolve phone/mobile in Python (avoids QWeb field access issues)
            phone = partner.phone or ''
            try:
                mobile = partner.mobile or ''
            except Exception:
                mobile = ''
            contact_phone = phone or mobile or '-'

            report_lines.append({
                'partner': partner,
                'partner_name': partner.name or '-',
                'partner_phone': contact_phone,
                'orders': orders_data,
                'total': partner_total,
                'order_count': len(pos_orders),
            })

        return {
            'doc_ids': docids,
            'doc_model': 'cash.customer.report.wizard',
            'report_lines': report_lines,
            'grand_total': grand_total,
            'grand_orders': grand_orders,
            'date_from': date_from or 'All',
            'date_to': date_to or 'All',
            'company': self.env.company,
        }
