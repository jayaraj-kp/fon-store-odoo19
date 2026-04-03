from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import os
import subprocess
import tempfile
import urllib.request
import urllib.error


class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Product Label Printing Wizard'

    product_tmpl_ids = fields.Many2many('product.template', string='Product Templates')
    product_ids = fields.Many2many('product.product', string='Product Variants')
    quantity = fields.Integer(string='Number of Labels per Product', default=1, required=True)
    label_width_mm = fields.Integer(string='Label Width (mm)', default=75)
    label_height_mm = fields.Integer(string='Label Height (mm)', default=30)
    columns = fields.Selection(
        [('1', '1 Column'), ('2', '2 Columns')],
        string='Columns per Row', default='2', required=True,
    )
    show_mrp = fields.Boolean(string='Show MRP', default=True)
    show_qr = fields.Boolean(string='Show QR Code', default=True)
    show_label_code = fields.Boolean(string='Show Label Code', default=True)
    print_server_url = fields.Char(
        string='Windows Print Server URL',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'product_label_print.print_server_url',
            'http://192.168.1.100:8899/print',
        ),
        help='URL of windows_print_server.py running on the Windows PC.\n'
             'Example: http://192.168.1.50:8899/print',
    )

    # ------------------------------------------------------------------
    # QR code helper — inline base64 PNG, no HTTP call needed
    # ------------------------------------------------------------------

    def _make_qr_base64(self, value):
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=4,
                border=1,
            )
            qr.add_data(value or 'LABEL')
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception:
            return (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
                'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
            )

    # ------------------------------------------------------------------
    # Label-code vertical text via Pillow
    # Renders text as a PNG rotated 90° CCW (reads bottom → top).
    # This avoids wkhtmltopdf's broken support for CSS writing-mode.
    # ------------------------------------------------------------------

    def _make_code_b64(self, text):
        try:
            from PIL import Image, ImageDraw, ImageFont

            DPI = 203
            PX = DPI / 25.4
            cell_w = int(8 * PX)               # 8 mm wide
            cell_h = int(26 * PX)              # 26 mm tall
            font_px = max(14, int(5.5 * PX / 72 * 10))

            font = ImageFont.load_default()
            for path in [
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
                '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf',
            ]:
                if os.path.exists(path):
                    try:
                        font = ImageFont.truetype(path, font_px)
                        break
                    except Exception:
                        pass

            # Draw text horizontally
            dummy = Image.new('RGB', (1, 1))
            bbox = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0] + 6, bbox[3] - bbox[1] + 6

            horiz = Image.new('RGB', (tw, th), 'white')
            ImageDraw.Draw(horiz).text((3, 3), text, fill='black', font=font)

            # Rotate 90° CCW → text reads bottom-to-top
            rotated = horiz.rotate(90, expand=True)

            # Centre in cell canvas
            canvas = Image.new('RGB', (cell_w, cell_h), 'white')
            px = max(0, (cell_w - rotated.width) // 2)
            py = max(0, (cell_h - rotated.height) // 2)
            canvas.paste(rotated, (px, py))

            buf = io.BytesIO()
            canvas.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode('ascii')

        except Exception:
            return ''

    # ------------------------------------------------------------------
    # Products / labels
    # ------------------------------------------------------------------

    def _get_products(self):
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    def _get_label_list(self):
        label_list = []
        for product in self._get_products():
            tmpl = product.product_tmpl_id
            label_code = getattr(tmpl, 'label_code', None) or product.default_code or ''
            mrp = int(tmpl.list_price or 0)
            qr_value = product.barcode or product.default_code or tmpl.name or str(product.id)

            # display_name includes variant attributes → "KEYCHAIN 110"
            name = (product.display_name or tmpl.name or '').upper()

            qr_b64 = self._make_qr_base64(qr_value)
            code_b64 = self._make_code_b64(label_code) if label_code else ''

            for _i in range(self.quantity):
                label_list.append({
                    'name': name,
                    'label_code': label_code,
                    'code_b64': code_b64,
                    'mrp': mrp,
                    'qr_b64': qr_b64,
                })
        return label_list

    # ------------------------------------------------------------------
    # HTML builder
    # ------------------------------------------------------------------

    def _build_label_html(self, label_list, col_count):
        css = """
        <style>
            * { margin:0; padding:0; box-sizing:border-box; }
            body { font-family:Arial,sans-serif; background:white; }
            table.sheet { border-collapse:separate; border-spacing:0; width:100%; }
            td.cell {
                border: 1px solid #888;
                border-radius: 3px;
                width: 73mm;
                height: 28mm;
                padding: 0;
                vertical-align: middle;
            }
            td.gap  { width:2mm; border:none; padding:0; }
            tr.rgap { height:1mm; }
            table.inner { border-collapse:collapse; width:100%; height:28mm; }
            td.qr-td   { width:26mm; text-align:center; vertical-align:middle; padding:1mm; }
            td.code-td { width:8mm;  text-align:center; vertical-align:middle; padding:0; }
            td.info-td { vertical-align:bottom; padding:1mm 1mm 2mm 1mm; }
            .pname { font-size:6pt; font-weight:bold; display:block; line-height:1.4; }
            .mrp   { font-size:5.5pt; display:block; margin-top:1mm; }
        </style>
        """

        rows = [label_list[i:i + col_count]
                for i in range(0, len(label_list), col_count)]
        html_rows = []

        for r_idx, row in enumerate(rows):
            cells = []
            for c_idx, lbl in enumerate(row):
                inner = ''

                if self.show_qr:
                    inner += (
                        '<td class="qr-td">'
                        '<img src="data:image/png;base64,{b64}"'
                        ' style="width:24mm;height:24mm;" alt="QR"/>'
                        '</td>'
                    ).format(b64=lbl['qr_b64'])

                if self.show_label_code and lbl.get('code_b64'):
                    inner += (
                        '<td class="code-td">'
                        '<img src="data:image/png;base64,{b64}"'
                        ' style="width:8mm;height:26mm;" alt="{code}"/>'
                        '</td>'
                    ).format(b64=lbl['code_b64'], code=lbl['label_code'])

                mrp_html = (
                    '<span class="mrp">MRP Rs&nbsp;&nbsp;{}</span>'.format(lbl['mrp'])
                ) if self.show_mrp else ''

                inner += (
                    '<td class="info-td">'
                    '<span class="pname">{name}</span>{mrp}'
                    '</td>'
                ).format(name=lbl['name'], mrp=mrp_html)

                cells.append(
                    '<td class="cell"><table class="inner"><tr>{}</tr></table></td>'
                    .format(inner)
                )
                if c_idx < len(row) - 1:
                    cells.append('<td class="gap"></td>')

            html_rows.append('<tr>{}</tr>'.format(''.join(cells)))
            if r_idx < len(rows) - 1:
                html_rows.append('<tr class="rgap"><td></td></tr>')

        return (
            '<!DOCTYPE html><html>'
            '<head><meta charset="utf-8"/>{css}</head>'
            '<body><table class="sheet">{rows}</table></body>'
            '</html>'
        ).format(css=css, rows=''.join(html_rows))

    # ------------------------------------------------------------------
    # Shared PDF generator
    # ------------------------------------------------------------------

    def _generate_pdf_bytes(self):
        col_count = int(self.columns)
        label_list = self._get_label_list()
        if not label_list:
            raise UserError(_('No labels to print.'))

        num_rows = (len(label_list) + col_count - 1) // col_count
        page_w = col_count * 75 + (col_count - 1) * 2   # 152 mm for 2-col
        page_h = num_rows * 30

        html = self._build_label_html(label_list, col_count)

        html_path = pdf_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False,
                                             mode='w', encoding='utf-8') as fh:
                fh.write(html)
                html_path = fh.name
            pdf_path = html_path.replace('.html', '.pdf')

            cmd = [
                'wkhtmltopdf',
                '--page-width',    '{}mm'.format(page_w),
                '--page-height',   '{}mm'.format(page_h),
                '--margin-top',    '0mm',
                '--margin-bottom', '0mm',
                '--margin-left',   '0mm',
                '--margin-right',  '0mm',
                '--disable-smart-shrinking',
                '--zoom', '1',
                '--no-stop-slow-scripts',
                '--disable-external-links',
                html_path, pdf_path,
            ]
            result = subprocess.run(cmd, capture_output=True)

            if result.returncode not in (0, 1) or not os.path.exists(pdf_path):
                raise UserError(
                    _('wkhtmltopdf failed:\n%s')
                    % result.stderr.decode('utf-8', errors='replace')
                )

            with open(pdf_path, 'rb') as f:
                return f.read()
        finally:
            for p in (html_path, pdf_path):
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # Action 1: Download PDF  (existing behaviour)
    # ------------------------------------------------------------------

    def action_print_labels(self):
        self.ensure_one()
        if not self._get_products():
            raise UserError(_('Please select at least one product.'))
        pdf_data = self._generate_pdf_bytes()
        att = self.env['ir.attachment'].create({
            'name': 'Product_Labels.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_data),
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(att.id),
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # Action 2: Send directly to GP-1125T via Windows print server
    # ------------------------------------------------------------------

    def action_direct_print(self):
        self.ensure_one()
        if not self._get_products():
            raise UserError(_('Please select at least one product.'))
        if not self.print_server_url:
            raise UserError(_(
                'Windows Print Server URL is empty.\n'
                'Enter the URL of the print server running on the Windows PC,\n'
                'e.g.  http://192.168.1.50:8899/print'
            ))

        pdf_data = self._generate_pdf_bytes()

        # Persist the URL as the new default
        self.env['ir.config_parameter'].sudo().set_param(
            'product_label_print.print_server_url',
            self.print_server_url,
        )

        try:
            req = urllib.request.Request(
                self.print_server_url,
                data=pdf_data,
                method='POST',
                headers={
                    'Content-Type': 'application/pdf',
                    'Content-Length': str(len(pdf_data)),
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Sent to Printer'),
                            'message': _('Labels sent to GP-1125T successfully!'),
                            'type': 'success',
                            'sticky': False,
                        },
                    }
                raise UserError(_('Print server returned HTTP %s') % resp.status)

        except urllib.error.URLError as exc:
            raise UserError(_(
                'Cannot reach print server at:\n  %s\n\n'
                'Error: %s\n\n'
                'Checklist:\n'
                '  1. windows_print_server.py is running on the Windows PC\n'
                '  2. The IP address in the URL is correct\n'
                '  3. Windows Firewall allows inbound TCP port 8899'
            ) % (self.print_server_url, exc.reason))


# below code is working (print)
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
# import base64
# import io
# import os
# import subprocess
# import tempfile
#
#
# class ProductLabelWizard(models.TransientModel):
#     _name = 'product.label.wizard'
#     _description = 'Product Label Printing Wizard'
#
#     product_tmpl_ids = fields.Many2many('product.template', string='Product Templates')
#     product_ids = fields.Many2many('product.product', string='Product Variants')
#     quantity = fields.Integer(string='Number of Labels per Product', default=1, required=True)
#     label_width_mm = fields.Integer(string='Label Width (mm)', default=75)
#     label_height_mm = fields.Integer(string='Label Height (mm)', default=30)
#     columns = fields.Selection(
#         [('1', '1 Column'), ('2', '2 Columns')],
#         string='Columns per Row', default='2', required=True,
#     )
#     show_mrp = fields.Boolean(string='Show MRP', default=True)
#     show_qr = fields.Boolean(string='Show QR Code', default=True)
#     show_label_code = fields.Boolean(string='Show Label Code', default=True)
#
#     # ------------------------------------------------------------------
#     # QR helper  (no network — purely in-process)
#     # ------------------------------------------------------------------
#
#     def _make_qr_base64(self, value):
#         """Return base64-encoded PNG of a QR code. Zero network calls."""
#         try:
#             import qrcode
#             qr = qrcode.QRCode(
#                 version=1,
#                 error_correction=qrcode.constants.ERROR_CORRECT_L,
#                 box_size=4,
#                 border=1,
#             )
#             qr.add_data(value or 'LABEL')
#             qr.make(fit=True)
#             img = qr.make_image(fill_color='black', back_color='white')
#             buf = io.BytesIO()
#             img.save(buf, format='PNG')
#             return base64.b64encode(buf.getvalue()).decode('ascii')
#         except Exception:
#             # 1×1 white PNG fallback so the rest of the label still prints
#             return (
#                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
#                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
#             )
#
#     # ------------------------------------------------------------------
#     # Product / label helpers
#     # ------------------------------------------------------------------
#
#     def _get_products(self):
#         products = self.env['product.product']
#         if self.product_ids:
#             products |= self.product_ids
#         if self.product_tmpl_ids:
#             for tmpl in self.product_tmpl_ids:
#                 products |= tmpl.product_variant_ids
#         return products
#
#     def _get_label_list(self):
#         products = self._get_products()
#         label_list = []
#         for product in products:
#             tmpl = product.product_tmpl_id
#             label_code = (getattr(tmpl, 'label_code', None) or
#                           product.default_code or '')
#             mrp = int(tmpl.list_price or 0)
#             qr_value = (product.barcode or product.default_code or
#                         tmpl.name or str(product.id))
#             qr_b64 = self._make_qr_base64(qr_value)
#             for _i in range(self.quantity):
#                 label_list.append({
#                     'name': tmpl.name or '',
#                     'label_code': label_code,
#                     'mrp': mrp,
#                     'qr_b64': qr_b64,
#                 })
#         return label_list
#
#     # ------------------------------------------------------------------
#     # HTML builder  (all images are inline base64 — wkhtmltopdf makes
#     #                ZERO external requests, so no ProtocolUnknownError)
#     # ------------------------------------------------------------------
#
#     def _build_label_html(self, label_list, col_count):
#         css = """
#         <style>
#             * { margin:0; padding:0; box-sizing:border-box; }
#             body { font-family:Arial,sans-serif; background:white; }
#             table.sheet { border-collapse:separate; border-spacing:0; width:100%; }
#             td.cell {
#                 border: 1px solid #888;
#                 border-radius: 3px;
#                 width: 73mm;
#                 height: 28mm;
#                 padding: 0;
#                 vertical-align: middle;
#             }
#             td.gap  { width:2mm; border:none; padding:0; }
#             tr.rgap { height:1mm; }
#             table.inner { border-collapse:collapse; width:100%; height:28mm; }
#             td.qr-td   { width:26mm; text-align:center; vertical-align:middle; padding:1mm; }
#             td.code-td { width:7mm;  text-align:center; vertical-align:middle; padding:0; }
#             .code-text {
#                 display: inline-block;
#                 writing-mode: vertical-rl;
#                 transform: rotate(180deg);
#                 font-size: 5pt;
#                 font-weight: bold;
#                 white-space: nowrap;
#             }
#             td.info-td { vertical-align:bottom; padding:1mm 1mm 2mm 1mm; }
#             .pname { font-size:6pt; font-weight:bold; text-transform:uppercase;
#                      display:block; line-height:1.4; }
#             .mrp   { font-size:5.5pt; display:block; margin-top:1mm; }
#         </style>
#         """
#
#         # Split into rows
#         rows = [label_list[i:i + col_count]
#                 for i in range(0, len(label_list), col_count)]
#
#         html_rows = []
#         for r_idx, row in enumerate(rows):
#             cells = []
#             for c_idx, lbl in enumerate(row):
#                 inner = ''
#
#                 if self.show_qr:
#                     inner += (
#                         '<td class="qr-td">'
#                         '<img src="data:image/png;base64,{b64}"'
#                         ' style="width:24mm;height:24mm;" alt="QR"/>'
#                         '</td>'
#                     ).format(b64=lbl['qr_b64'])
#
#                 if self.show_label_code and lbl.get('label_code'):
#                     inner += (
#                         '<td class="code-td">'
#                         '<span class="code-text">{code}</span>'
#                         '</td>'
#                     ).format(code=lbl['label_code'])
#
#                 mrp_html = (
#                     '<span class="mrp">MRP Rs&nbsp;&nbsp;{mrp}</span>'
#                     .format(mrp=lbl['mrp'])
#                 ) if self.show_mrp else ''
#
#                 inner += (
#                     '<td class="info-td">'
#                     '<span class="pname">{name}</span>{mrp}'
#                     '</td>'
#                 ).format(name=lbl['name'], mrp=mrp_html)
#
#                 cells.append(
#                     '<td class="cell">'
#                     '<table class="inner"><tr>{inner}</tr></table>'
#                     '</td>'.format(inner=inner)
#                 )
#                 if c_idx < len(row) - 1:
#                     cells.append('<td class="gap"></td>')
#
#             html_rows.append('<tr>{}</tr>'.format(''.join(cells)))
#             if r_idx < len(rows) - 1:
#                 html_rows.append('<tr class="rgap"><td></td></tr>')
#
#         return (
#             '<!DOCTYPE html><html>'
#             '<head><meta charset="utf-8"/>{css}</head>'
#             '<body><table class="sheet">{rows}</table></body>'
#             '</html>'
#         ).format(css=css, rows=''.join(html_rows))
#
#     # ------------------------------------------------------------------
#     # Action
#     # ------------------------------------------------------------------
#
#     def action_print_labels(self):
#         self.ensure_one()
#         products = self._get_products()
#         if not products:
#             raise UserError(_('Please select at least one product.'))
#
#         col_count = int(self.columns)
#         label_list = self._get_label_list()
#         num_rows = (len(label_list) + col_count - 1) // col_count
#
#         # Page dimensions:
#         #   width  = 2 labels × 75mm + 2mm gap = 152mm  (1-col: 76mm)
#         #   height = rows × 30mm  (no fixed paper, thermal roll)
#         page_w = (col_count * 75) + ((col_count - 1) * 2)
#         page_h = num_rows * 30
#
#         html_content = self._build_label_html(label_list, col_count)
#
#         html_path = pdf_path = None
#         try:
#             with tempfile.NamedTemporaryFile(
#                     suffix='.html', delete=False,
#                     mode='w', encoding='utf-8') as fh:
#                 fh.write(html_content)
#                 html_path = fh.name
#
#             pdf_path = html_path.replace('.html', '.pdf')
#
#             cmd = [
#                 'wkhtmltopdf',
#                 '--page-width',  '{}mm'.format(page_w),
#                 '--page-height', '{}mm'.format(page_h),
#                 '--margin-top',    '0mm',
#                 '--margin-bottom', '0mm',
#                 '--margin-left',   '0mm',
#                 '--margin-right',  '0mm',
#                 '--disable-smart-shrinking',
#                 '--zoom', '1',
#                 '--no-stop-slow-scripts',
#                 # images are base64 inline — no external load needed:
#                 '--disable-external-links',
#                 html_path,
#                 pdf_path,
#             ]
#             result = subprocess.run(cmd, capture_output=True)
#
#             # wkhtmltopdf may warn but still produce a valid PDF (exit 0 or 1)
#             if result.returncode not in (0, 1) or not os.path.exists(pdf_path):
#                 err = result.stderr.decode('utf-8', errors='replace')
#                 raise UserError(
#                     _('wkhtmltopdf failed (exit %s):\n%s')
#                     % (result.returncode, err)
#                 )
#
#             with open(pdf_path, 'rb') as f:
#                 pdf_data = f.read()
#
#         finally:
#             for p in (html_path, pdf_path):
#                 if p and os.path.exists(p):
#                     try:
#                         os.unlink(p)
#                     except Exception:
#                         pass
#
#         attachment = self.env['ir.attachment'].create({
#             'name': 'Product_Labels.pdf',
#             'type': 'binary',
#             'datas': base64.b64encode(pdf_data),
#             'mimetype': 'application/pdf',
#             'res_model': self._name,
#             'res_id': self.id,
#         })
#
#         return {
#             'type': 'ir.actions.act_url',
#             'url': '/web/content/{}?download=true'.format(attachment.id),
#             'target': 'new',
#         }