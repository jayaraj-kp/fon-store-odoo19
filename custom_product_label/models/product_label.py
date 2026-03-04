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
        help='Instagram username or URL for QR code on label (e.g. @yourshop or https://instagram.com/yourshop)'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_barcode_image_b64(self):
        """Generate barcode image (no text) as base64 PNG."""
        barcode_val = self.barcode
        if not barcode_val:
            return False
        if not HAS_BARCODE:
            _logger.warning("python-barcode not installed. Run: pip install python-barcode[images]")
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
        """Generate Instagram QR code as base64 PNG."""
        handle = self.product_tmpl_id.instagram_handle
        if not handle:
            # fallback: use company instagram if set, else skip
            handle = self.env.company.instagram_handle if hasattr(self.env.company, 'instagram_handle') else ''
        if not handle:
            return False
        if not HAS_QRCODE:
            _logger.warning("qrcode not installed. Run: pip install qrcode[pil]")
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
            _logger.error("QR generation error: %s", e)
            return False

    def get_label_price(self):
        """Return the MRP / list price formatted."""
        price = self.lst_price
        return "₹{:,.2f}".format(price)


class ResCompany(models.Model):
    _inherit = 'res.company'

    instagram_handle = fields.Char(
        string='Instagram Handle',
        help='Company-wide Instagram handle used on product labels if product has none.'
    )
