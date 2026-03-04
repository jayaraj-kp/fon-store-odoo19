import base64
import io
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    instagram_handle = fields.Char(
        string='Instagram Handle',
        help='Instagram username or URL for QR code on label'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_barcode_image_b64(self):
        barcode_val = self.barcode
        if not barcode_val:
            return False
        if not HAS_BARCODE:
            return False
        try:
            buf = io.BytesIO()
            options = {
                'write_text': False,
                'module_height': 8.0,
                'module_width': 0.18,
                'quiet_zone': 1.0,
                'font_size': 0,
                'text_distance': 0,
            }
            Code128(barcode_val, writer=ImageWriter()).write(buf, options=options)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            _logger.error("Barcode generation error: %s", e)
            return False

    def get_instagram_qr_b64(self):
        handle = self.product_tmpl_id.instagram_handle
        if not handle:
            handle = self.env.company.instagram_handle if hasattr(self.env.company, 'instagram_handle') else ''
        if not handle:
            return False
        if not HAS_QRCODE:
            return False
        try:
            if not handle.startswith('http'):
                handle = 'https://instagram.com/' + handle.lstrip('@')
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=3, border=1)
            qr.add_data(handle)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            _logger.error("QR generation error: %s", e)
            return False

    def get_label_price(self):
        return "₹{:,.2f}".format(self.lst_price)


class ResCompany(models.Model):
    _inherit = 'res.company'

    instagram_handle = fields.Char(string='Instagram Handle')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _run_wkhtmltopdf(self, bodies, report_ref=False, header=None, footer=None,
                         landscape=False, specific_paperformat_args=None, set_viewport_size=False):
        """Force 50x25mm page size for our custom label report."""
        report_sudo = self._get_report(report_ref) if report_ref else self
        if report_sudo and report_sudo.report_name == 'custom_product_label.report_product_label_template':
            if specific_paperformat_args is None:
                specific_paperformat_args = {}
            specific_paperformat_args['data-report-page-width'] = 50
            specific_paperformat_args['data-report-page-height'] = 25
            specific_paperformat_args['data-report-margin-top'] = 0
            specific_paperformat_args['data-report-margin-bottom'] = 0
            specific_paperformat_args['data-report-margin-left'] = 0
            specific_paperformat_args['data-report-margin-right'] = 0
            landscape = False
        return super()._run_wkhtmltopdf(
            bodies, report_ref=report_ref, header=header, footer=footer,
            landscape=landscape, specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size
        )
