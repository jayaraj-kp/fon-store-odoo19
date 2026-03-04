import io
import logging
import re
from urllib.parse import unquote, quote

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class PosUpiQrController(http.Controller):

    @http.route(
        '/pos/upi_qr',
        type='http',
        auth='user',
        methods=['GET'],
        csrf=False,
    )
    def generate_upi_qr(self, vpa='', name='Store', amount='0', note='POS Payment', **kwargs):
        try:
            import qrcode

            # Step 1: Decode URL-encoded characters from the HTTP query string (e.g. %40 → @)
            vpa    = unquote(vpa).strip()
            name   = unquote(name).strip()
            note   = unquote(note).strip()

            # Step 2: Sanitise amount — keep only digits and one decimal point
            try:
                amount = f"{float(re.sub(r'[^0-9.]', '', amount or '0')):.2f}"
            except (ValueError, TypeError):
                amount = '0.00'

            # Step 3: Re-encode values for use *inside* the UPI deep-link URI.
            # Without this, names/notes with spaces or special chars break the QR.
            upi_url = (
                f"upi://pay"
                f"?pa={quote(vpa, safe='@.')}"   # @ and . are valid in a VPA
                f"&pn={quote(name, safe='')}"
                f"&am={amount}"                   # numeric — no encoding needed
                f"&cu=INR"
                f"&tn={quote(note, safe='')}"
            )

            _logger.debug("custom_pos_upi_qr: generating QR for %s", upi_url)

            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=7,
                border=3,
            )
            qr.add_data(upi_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color='black', back_color='white')

            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)

            return Response(
                buffer.read(),
                content_type='image/png',
                headers=[
                    ('Cache-Control', 'no-store'),
                    ('X-Content-Type-Options', 'nosniff'),
                ],
            )

        except ImportError:
            _logger.warning(
                "custom_pos_upi_qr: 'qrcode' library not found. "
                "Install it with:  pip install \"qrcode[pil]\""
            )
            transparent_1x1 = bytes([
                0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,
                0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
                0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,
                0x08,0x06,0x00,0x00,0x00,0x1F,0x15,0xC4,
                0x89,0x00,0x00,0x00,0x0A,0x49,0x44,0x41,
                0x54,0x78,0x9C,0x62,0x00,0x01,0x00,0x00,
                0x05,0x00,0x01,0x0D,0x0A,0x2D,0xB4,0x00,
                0x00,0x00,0x00,0x49,0x45,0x4E,0x44,0xAE,
                0x42,0x60,0x82,
            ])
            return Response(transparent_1x1, content_type='image/png')

        except Exception as exc:
            _logger.error("custom_pos_upi_qr: QR generation failed: %s", exc)
            return Response('', status=500)