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
    _logger.warning("qrcode not installed: pip install qrcode[pil]")

try:
    from barcode import Code128
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False
    _logger.warning("python-barcode not installed: pip install python-barcode[images]")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    instagram_handle = fields.Char(
        string='Instagram Handle',
        help='e.g. @yourshop or https://instagram.com/yourshop'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_barcode_image_b64(self):
        """Generate barcode as base64 PNG with no text underneath."""
        if not self.barcode:
            _logger.warning("Product %s has no barcode", self.name)
            return False
        if not HAS_BARCODE:
            _logger.warning("python-barcode not installed")
            return False
        try:
            buf = io.BytesIO()
            Code128(str(self.barcode), writer=ImageWriter()).write(buf, options={
                'write_text': False,
                'module_height': 10.0,
                'module_width': 0.2,
                'quiet_zone': 2.0,
                'dpi': 200,
            })
            buf.seek(0)
            result = base64.b64encode(buf.read()).decode('utf-8')
            _logger.info("Barcode generated for %s, length=%d", self.barcode, len(result))
            return result
        except Exception as e:
            _logger.error("Barcode error for %s: %s", self.barcode, e)
            return False

    def get_instagram_qr_b64(self):
        """Generate Instagram QR code as base64 PNG."""
        handle = self.product_tmpl_id.instagram_handle or \
                 getattr(self.env.company, 'instagram_handle', '')
        if not handle:
            return False
        if not HAS_QRCODE:
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
        """Return company logo as base64 string for embedding in HTML."""
        company = self.company_id or self.env.company
        if not company.logo:
            return False
        try:
            # company.logo is already base64 encoded bytes in Odoo
            logo = company.logo
            if isinstance(logo, bytes):
                # decode bytes to string (it's already base64)
                return logo.decode('utf-8')
            # it's already a string
            return logo
        except Exception as e:
            _logger.error("Logo error: %s", e)
            return False


class ResCompany(models.Model):
    _inherit = 'res.company'

    instagram_handle = fields.Char(string='Instagram Handle (Labels)')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _build_wkhtmltopdf_args(self, paperformat_id, landscape,
                                 specific_paperformat_args=None,
                                 set_viewport_size=False):
        args = super()._build_wkhtmltopdf_args(
            paperformat_id, landscape,
            specific_paperformat_args=specific_paperformat_args,
            set_viewport_size=set_viewport_size,
        )
        if paperformat_id and paperformat_id.name == 'FON Label 50x25mm':
            new_args = []
            skip_next = False
            for arg in args:
                if skip_next:
                    skip_next = False
                    continue
                if arg in ('--margin-top', '--margin-bottom',
                           '--margin-left', '--margin-right',
                           '--header-spacing'):
                    new_args.append(arg)
                    new_args.append('0')
                    skip_next = True
                elif arg == '--orientation':
                    skip_next = True
                elif arg in ('--header-html', '--footer-html'):
                    skip_next = True
                else:
                    new_args.append(arg)
            _logger.info("FON Label wkhtmltopdf args: %s", new_args)
            return new_args
        return args
