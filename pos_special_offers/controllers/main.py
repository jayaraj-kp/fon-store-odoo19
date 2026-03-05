import csv
import io
from odoo import http
from odoo.http import request


class PosSpecialOfferController(http.Controller):

    @http.route('/pos_special_offers/export_coupons/<int:offer_id>',
                type='http', auth='user')
    def export_coupons(self, offer_id, **kwargs):
        offer = request.env['pos.special.offer'].browse(offer_id)
        if not offer.exists():
            return request.not_found()

        coupons = request.env['pos.special.offer.coupon'].search([
            ('offer_id', '=', offer_id),
        ], order='create_date desc')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Code', 'Status', 'Times Used', 'Active'])
        for c in coupons:
            writer.writerow([c.code, c.state, c.used_count, 'Yes' if c.active else 'No'])

        filename = f"coupons_{offer.name.replace(' ', '_')}.csv"
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'text/csv;charset=utf-8'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ]
        )
