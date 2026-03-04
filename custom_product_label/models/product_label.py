import base64
import io
import logging

from odoo import fields, models

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

    instagram_handle = fields.Char(string='Instagram Handle',
        help='e.g. @yourshop or https://instagram.com/yourshop')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_barcode_image_b64(self):
        if not self.barcode or not HAS_BARCODE:
            return False
        try:
            buf = io.BytesIO()
            Code128(self.barcode, writer=ImageWriter()).write(buf, options={
                'write_text': False, 'module_height': 8.0,
                'module_width': 0.18, 'quiet_zone': 1.0,
            })
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            _logger.error("Barcode error: %s", e)
            return False

    def get_instagram_qr_b64(self):
        handle = self.product_tmpl_id.instagram_handle or \
                 getattr(self.env.company, 'instagram_handle', '')
        if not handle or not HAS_QRCODE:
            return False
        try:
            if not handle.startswith('http'):
                handle = 'https://instagram.com/' + handle.lstrip('@')
            qr = qrcode.QRCode(version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3, border=1)
            qr.add_data(handle)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        except Exception as e:
            _logger.error("QR error: %s", e)
            return False

    def get_label_price(self):
        return u"\u20b9{:,.2f}".format(self.lst_price)


class ResCompany(models.Model):
    _inherit = 'res.company'

    instagram_handle = fields.Char(string='Instagram Handle (Labels)')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, paperformat_id, landscape,
                                 specific_paperformat_args=None,
                                 set_viewport_size=False):
        """
        Override to force correct page size for our label report.
        Logs all args so we can debug what wkhtmltopdf actually receives.
        """
        args = super()._build_wkhtmltopdf_args(
            paperformat_id, landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size
        )
        _logger.warning("LABEL DEBUG _build_wkhtmltopdf_args CALLED, args=%s", args)
        return args

    def _run_wkhtmltopdf(self, bodies, report_ref=False, header=None,
                          footer=None, landscape=False,
                          specific_paperformat_args=None,
                          set_viewport_size=False):
        _logger.warning("LABEL DEBUG _run_wkhtmltopdf CALLED report_ref=%s", report_ref)
        _logger.warning("LABEL DEBUG specific_paperformat_args=%s", specific_paperformat_args)
        _logger.warning("LABEL DEBUG landscape=%s", landscape)

        # Check if it's our report and force page size
        try:
            report = self._get_report(report_ref) if report_ref else None
            if report:
                _logger.warning("LABEL DEBUG report.report_name=%s", report.report_name)
                _logger.warning("LABEL DEBUG paperformat=%s", report.paperformat_id)
                if report.paperformat_id:
                    pf = report.paperformat_id
                    _logger.warning("LABEL DEBUG pf.page_width=%s pf.page_height=%s",
                                    pf.page_width, pf.page_height)
        except Exception as ex:
            _logger.warning("LABEL DEBUG error inspecting report: %s", ex)

        return super()._run_wkhtmltopdf(
            bodies, report_ref=report_ref, header=header,
            footer=footer, landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size
        )
