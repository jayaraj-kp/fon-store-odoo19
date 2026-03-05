from odoo import models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def get_pos_orders_for_session(self, session_id):
        """
        Fetch all completed orders for the given POS session.
        Returns a list of dicts for display in the POS Invoice screen.
        Does NOT require the accounting module.
        """
        orders = self.search([
            ('session_id', '=', session_id),
            ('state', 'in', ['paid', 'done', 'invoiced']),
        ], order='date_order desc')

        result = []
        for order in orders:
            lines = []
            for line in order.lines:
                lines.append({
                    'product_name': line.product_id.name or '',
                    'qty': line.qty,
                    'price_unit': line.price_unit,
                    'price_subtotal': line.price_subtotal,
                })
            result.append({
                'id': order.id,
                'name': order.name,
                'date_order': str(order.date_order),
                'partner_name': order.partner_id.name if order.partner_id else 'Walk-in Customer',
                'amount_tax': order.amount_tax,
                'amount_total': order.amount_total,
                'state': order.state,
                'lines': lines,
            })
        return result
