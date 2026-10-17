import csv
import io
import re

from odoo import http
from odoo.http import request


def _safe_cell(value):
    """Neutralise spreadsheet formula injection."""
    value = '' if value is None else str(value)
    return "'" + value if value[:1] in ('=', '+', '-', '@') else value


class PosSpecialOfferController(http.Controller):

    @http.route('/pos_special_offers/export_coupons/<int:offer_id>',
                type='http', auth='user', methods=['GET'])
    def export_coupons(self, offer_id, **kwargs):
        if not request.env.user.has_group('point_of_sale.group_pos_manager'):
            return request.make_response('Forbidden', status=403)

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
            writer.writerow([_safe_cell(c.code), c.state, c.used_count,
                             'Yes' if c.active else 'No'])

        safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', offer.name or 'offer')
        filename = f"coupons_{safe_name}.csv"
        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'text/csv;charset=utf-8'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ]
        )

# import csv
# import io
# from odoo import http
# from odoo.http import request
#
#
# class PosSpecialOfferController(http.Controller):
#
#     @http.route('/pos_special_offers/export_coupons/<int:offer_id>',
#                 type='http', auth='user')
#     def export_coupons(self, offer_id, **kwargs):
#         offer = request.env['pos.special.offer'].browse(offer_id)
#         if not offer.exists():
#             return request.not_found()
#
#         coupons = request.env['pos.special.offer.coupon'].search([
#             ('offer_id', '=', offer_id),
#         ], order='create_date desc')
#
#         output = io.StringIO()
#         writer = csv.writer(output)
#         writer.writerow(['Code', 'Status', 'Times Used', 'Active'])
#         for c in coupons:
#             writer.writerow([c.code, c.state, c.used_count, 'Yes' if c.active else 'No'])
#
#         filename = f"coupons_{offer.name.replace(' ', '_')}.csv"
#         return request.make_response(
#             output.getvalue(),
#             headers=[
#                 ('Content-Type', 'text/csv;charset=utf-8'),
#                 ('Content-Disposition', f'attachment; filename="{filename}"'),
#             ]
#         )
