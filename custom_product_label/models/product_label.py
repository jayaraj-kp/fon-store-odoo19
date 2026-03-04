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

    instagram_handle = fields.Char(
        string='Instagram Handle',
        help='e.g. @yourshop or https://instagram.com/yourshop'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_barcode_image_b64(self):
        if not self.barcode or not HAS_BARCODE:
            return False
        try:
            buf = io.BytesIO()
            Code128(self.barcode, writer=ImageWriter()).write(buf, options={
                'write_text': False,
                'module_height': 8.0,
                'module_width': 0.18,
                'quiet_zone': 1.0,
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
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
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

    def get_company_logo_b64(self):
        """Return company logo as base64 - avoids wkhtmltopdf network errors."""
        company = self.company_id or self.env.company
        if company.logo:
            logo = company.logo
            if isinstance(logo, bytes):
                return logo.decode('utf-8')
            return logo
        return False


class ResCompany(models.Model):
    _inherit = 'res.company'

    instagram_handle = fields.Char(string='Instagram Handle (Labels)')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, paperformat_id, landscape,
                                 specific_paperformat_args=None,
                                 set_viewport_size=False):
        """
        For our 50x25mm label:
        - Force all margins to 0
        - Remove --orientation flag (width > height already defines landscape)
        - Keep page-width=50mm, page-height=25mm
        """
        args = super()._build_wkhtmltopdf_args(
            paperformat_id, landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )

        if paperformat_id and paperformat_id.page_width == 50 and paperformat_id.page_height == 25:
            new_args = []
            skip_next = False
            for arg in args:
                if skip_next:
                    skip_next = False
                    continue
                # Zero out all margins and header spacing
                if arg in ('--margin-top', '--margin-bottom',
                           '--margin-left', '--margin-right',
                           '--header-spacing'):
                    new_args.append(arg)
                    new_args.append('0')
                    skip_next = True
                # Remove orientation flag - width/height already defines it
                elif arg == '--orientation':
                    skip_next = True  # skip the value too
                # Remove header/footer html files
                elif arg in ('--header-html', '--footer-html'):
                    skip_next = True
                else:
                    new_args.append(arg)

            _logger.info("LABEL 50x25 final args: %s", new_args)
            return new_args

        return args
