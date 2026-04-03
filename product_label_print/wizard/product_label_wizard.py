from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import os
import subprocess
import tempfile


class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Product Label Printing Wizard'

    product_tmpl_ids = fields.Many2many('product.template', string='Product Templates')
    product_ids = fields.Many2many('product.product', string='Product Variants')
    quantity = fields.Integer(string='Number of Labels per Product', default=1, required=True)
    show_mrp = fields.Boolean(string='Show MRP', default=True)
    show_qr = fields.Boolean(string='Show QR Code', default=True)
    show_label_code = fields.Boolean(string='Show Label Code', default=True)

    # ── QR generator ──────────────────────────────────────────────────────────

    def _make_qr_base64(self, value):
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
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

    # ── Product / label helpers ───────────────────────────────────────────────

    def _get_products(self):
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    def _get_label_list(self):
        products = self._get_products()
        label_list = []
        for product in products:
            tmpl = product.product_tmpl_id
            label_code = (getattr(tmpl, 'label_code', None) or
                          product.default_code or '')
            mrp = int(tmpl.list_price or 0)
            qr_value = (product.barcode or product.default_code or
                        tmpl.name or str(product.id))
            qr_b64 = self._make_qr_base64(qr_value)
            for _i in range(self.quantity):
                label_list.append({
                    'name': tmpl.name or '',
                    'label_code': label_code,
                    'mrp': mrp,
                    'qr_b64': qr_b64,
                })
        return label_list

    # ── HTML builder ──────────────────────────────────────────────────────────

    def _build_html(self, label_list):
        """
        GP-1125T roll: 152mm wide, labels feed horizontally.

        Each label = two stacked cells (solid outer border, dashed divider):
        ┌──────────────────────────┐
        │   [QR]   KC110           │  top cell  (QR_H mm tall)
        ├╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
        │  KEYCHAIN 110            │  bottom cell (BOT_H mm tall)
        │  MRP Rs. 110             │
        └──────────────────────────┘

        2 labels per row, side by side.

        Page width  = 152mm  (full roll width)
        Page height = num_rows × (QR_H + BOT_H + ROW_GAP) + top/bottom margin

        wkhtmltopdf flags:
          --page-width  152mm
          --page-height <calculated>mm
          --margin-*    0            (we control all spacing in HTML)
          --disable-smart-shrinking  (critical — prevents auto-scale)
          --zoom 1
          --dpi 203
        """

        # ── Dimensions (all in mm) ──────────────────────────────────────────
        LW      = 65    # label width
        QR_H    = 26    # top cell height  (QR area)
        BOT_H   = 28    # bottom cell height (name/MRP)
        LH      = QR_H + BOT_H   # 53mm total per label
        QR_SIZE = 18    # QR image size
        COL_GAP = 60    # gap between 2 label columns
        ROW_GAP = 4     # gap between label rows
        L_MAR   = 5     # fixed left margin
        PW      = 160   # page/roll width mm (wider to fit the gap)

        def one_label(lbl):
            # ── Top cell: QR image with label code vertically on right side ──
            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
                    'display:block;" alt=""/>'
                )

            code_html = ''
            if self.show_label_code and lbl.get('label_code'):
                # Use transform rotate on a fixed-size span — wkhtmltopdf does not support writing-mode
                code_html = (
                    '<td style="vertical-align:middle;width:6mm;padding-left:1mm;">'
                    '<div style="'
                    'width:6mm;'
                    'height:' + str(QR_SIZE) + 'mm;'
                    'overflow:visible;'
                    'position:relative;'
                    '">'
                    '<span style="'
                    'position:absolute;'
                    'top:50%;'
                    'left:50%;'
                    'white-space:nowrap;'
                    'font-size:10pt;font-weight:bold;'
                    'letter-spacing:0.8mm;'
                    'transform:translate(-50%,-50%) rotate(-90deg);'
                    '-webkit-transform:translate(-50%,-50%) rotate(-90deg);'
                    '">'
                    + lbl['label_code'] +
                    '</span>'
                    '</div>'
                    '</td>'
                )

            top_cell = (
                '<tr><td style="'
                'height:' + str(QR_H) + 'mm;'
                'padding:2mm 1mm 1mm 1mm;'
                'vertical-align:top;'
                'text-align:center;'
                'border-bottom:1.5px dashed #aaa;'
                '">'
                '<table style="border-collapse:collapse;margin:0 auto;"><tr>'
                '<td style="vertical-align:middle;">' + qr_html + '</td>'
                + code_html +
                '</tr></table>'
                '</td></tr>'
            )

            # ── Bottom cell: product name + MRP ──
            mrp_html = ''
            if self.show_mrp:
                mrp_html = (
                    '<div style="font-size:12pt;font-weight:bold;margin-top:2mm;text-align:center;">'
                    'MRP Rs. ' + str(lbl['mrp']) + '</div>'
                )

            bot_cell = (
                '<tr><td style="'
                'height:' + str(BOT_H) + 'mm;'
                'padding:8mm 1mm 0mm 1mm;'
                'vertical-align:top;'
                'text-align:center;'
                '">'
                '<div style="font-size:16pt;font-weight:bold;'
                'text-transform:uppercase;white-space:nowrap;">'
                + (lbl['name'] or '') + '</div>'
                + mrp_html +
                '</td></tr>'
            )

            return (
                '<table style="'
                'border-collapse:collapse;'
                'width:' + str(LW) + 'mm;'
                'border:1.5px solid #888;'
                'border-radius:3mm;'
                'background:white;'
                'table-layout:fixed;">'
                + top_cell + bot_cell +
                '</table>'
            )

        # ── Build row pairs ──────────────────────────────────────────────────
        rows_html = []
        i = 0
        while i < len(label_list):
            left  = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            rows_html.append(
                '<tr>'
                '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
                + one_label(left) + '</td>'
                '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
                '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
                + (one_label(right) if right else '') + '</td>'
                '</tr>'
                '<tr><td colspan="3" style="height:' + str(ROW_GAP) + 'mm;'
                'border:none;padding:0;"></td></tr>'
            )

        # ── Page height: exact fit to content ────────────────────────────────
        num_pairs = (len(label_list) + 1) // 2
        page_h = 2 + num_pairs * (LH + ROW_GAP) + 2   # 2mm top + 2mm bottom margin

        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<style>'
            '* { margin:0; padding:0; box-sizing:border-box; }'
            'html, body {'
            '  font-family: Arial, Helvetica, sans-serif;'
            '  background: white;'
            '  width: ' + str(PW) + 'mm;'
            '}'
            '</style></head>'
            '<body>'
            '<div style="padding-top:2mm;padding-left:' + str(L_MAR) + 'mm;">'
            '<table style="'
            'width:' + str(2 * LW + COL_GAP) + 'mm;'
            'border-collapse:separate;'
            'border-spacing:0;'
            'table-layout:fixed;">'
            + ''.join(rows_html) +
            '</table>'
            '</div>'
            '</body></html>'
        )

        return html, PW, page_h

    # ── Print action ──────────────────────────────────────────────────────────

    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        label_list = self._get_label_list()
        html_content, page_w, page_h = self._build_html(label_list)

        html_path = pdf_path = None
        try:
            with tempfile.NamedTemporaryFile(
                    suffix='.html', delete=False,
                    mode='w', encoding='utf-8') as fh:
                fh.write(html_content)
                html_path = fh.name

            pdf_path = html_path.replace('.html', '.pdf')

            cmd = [
                'wkhtmltopdf',
                # ── Page size: exactly the roll width × content height ──
                '--page-width',     str(page_w) + 'mm',
                '--page-height',    str(page_h) + 'mm',
                # ── Zero margins (all spacing is in the HTML) ──
                '--margin-top',     '0',
                '--margin-bottom',  '0',
                '--margin-left',    '0',
                '--margin-right',   '0',
                # ── Critical: prevent wkhtmltopdf from rescaling content ──
                '--disable-smart-shrinking',
                '--zoom',           '1',
                '--dpi',            '203',
                '--no-stop-slow-scripts',
                '--encoding',       'UTF-8',
                html_path,
                pdf_path,
            ]
            result = subprocess.run(cmd, capture_output=True)

            if result.returncode not in (0, 1) or not os.path.exists(pdf_path):
                err = result.stderr.decode('utf-8', errors='replace')
                raise UserError(
                    _('wkhtmltopdf failed (exit %s):\n%s')
                    % (result.returncode, err)
                )

            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()

        finally:
            for p in (html_path, pdf_path):
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except Exception:
                        pass

        attachment = self.env['ir.attachment'].create({
            'name': 'Product_Labels.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_data),
            'mimetype': 'application/pdf',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/' + str(attachment.id) + '?download=true',
            'target': 'new',
        }
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
#             td.qr-td   { width:26mm; text-align:center; vertical-align:top; padding:1mm; }
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