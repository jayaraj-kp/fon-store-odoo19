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

    def _make_qr_base64(self, value):
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=6,
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

    def _build_html(self, label_list):
        """
        Physical die-cut roll layout — each product occupies TWO separate label cells:

          Row A  ┌──────────┐  ┌──────────┐   ← QR label (separate cut)
                 │  [QR]    │  │  [QR]    │
                 │  KC110   │  │  KC110   │
                 └──────────┘  └──────────┘
                 (small gap between cuts)
          Row B  ┌──────────┐  ┌──────────┐   ← Name label (separate cut)
                 │KEYCHAIN  │  │KEYCHAIN  │
                 │MRP Rs.110│  │MRP Rs.110│
                 └──────────┘  └──────────┘

        Labels come in pairs of rows (QR row + Name row).
        2 columns per row matching the physical die-cut positions on the roll.
        """

        LW    = 65    # label width mm
        LH_Q  = 33    # QR label height mm
        LH_N  = 20    # Name/MRP label height mm
        QR_MM = 22    # QR image size mm
        CGAP  = 2     # gap between left and right column mm
        IGAP  = 2     # gap between QR label and Name label (inner gap) mm
        RGAP  = 4     # gap between successive product pairs mm
        PW    = 152   # roll width mm

        # Cell style helpers
        CELL_STYLE = (
            'border:1.5px solid #999;border-radius:3mm;'
            'background:white;overflow:hidden;'
        )

        def qr_cell(lbl):
            """Top label: QR code centred + label code below."""
            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + str(QR_MM) + 'mm;height:' + str(QR_MM) + 'mm;'
                    'display:block;margin:0 auto 1.5mm auto;" alt=""/>'
                )
            code_html = ''
            if self.show_label_code and lbl.get('label_code'):
                code_html = (
                    '<div style="text-align:center;font-size:7pt;font-weight:bold;'
                    'letter-spacing:0.3mm;white-space:nowrap;">'
                    + lbl['label_code'] + '</div>'
                )
            return (
                '<td style="width:' + str(LW) + 'mm;height:' + str(LH_Q) + 'mm;'
                + CELL_STYLE +
                'padding:2mm 1mm 1mm 1mm;vertical-align:middle;text-align:center;">'
                + qr_html + code_html +
                '</td>'
            )

        def name_cell(lbl):
            """Bottom label: product name + MRP centred."""
            mrp_html = ''
            if self.show_mrp:
                mrp_html = (
                    '<div style="font-size:6pt;margin-top:1.5mm;'
                    'text-align:center;white-space:nowrap;">'
                    'MRP Rs. ' + str(lbl['mrp']) + '</div>'
                )
            return (
                '<td style="width:' + str(LW) + 'mm;height:' + str(LH_N) + 'mm;'
                + CELL_STYLE +
                'padding:1.5mm 1mm;vertical-align:middle;text-align:center;">'
                '<div style="font-size:7.5pt;font-weight:bold;text-transform:uppercase;'
                'white-space:nowrap;">' + (lbl['name'] or '') + '</div>'
                + mrp_html +
                '</td>'
            )

        def gap_col():
            return '<td style="width:' + str(CGAP) + 'mm;border:none;padding:0;"></td>'

        def spacer_row(height_mm, colspan=3):
            return (
                '<tr><td colspan="' + str(colspan) + '" '
                'style="height:' + str(height_mm) + 'mm;border:none;padding:0;"></td></tr>'
            )

        rows_html = []
        i = 0
        while i < len(label_list):
            left  = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            right_qr_td   = qr_cell(right)   if right else '<td style="width:' + str(LW) + 'mm;border:none;"></td>'
            right_name_td = name_cell(right)  if right else '<td style="width:' + str(LW) + 'mm;border:none;"></td>'

            # QR row
            rows_html.append(
                '<tr>'
                + qr_cell(left) + gap_col() + right_qr_td +
                '</tr>'
            )
            # Inner gap between QR label and Name label
            rows_html.append(spacer_row(IGAP))
            # Name row
            rows_html.append(
                '<tr>'
                + name_cell(left) + gap_col() + right_name_td +
                '</tr>'
            )
            # Gap before next product pair
            rows_html.append(spacer_row(RGAP))

        num_pairs = (len(label_list) + 1) // 2
        page_h = num_pairs * (LH_Q + IGAP + LH_N + RGAP) + 6

        lmargin = (PW - (2 * LW + CGAP)) // 2  # centre on roll = 10mm

        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<style>'
            '* { margin:0; padding:0; box-sizing:border-box; }'
            'html,body { font-family:Arial,Helvetica,sans-serif; background:white; }'
            '</style></head>'
            '<body>'
            '<div style="margin-left:' + str(lmargin) + 'mm;padding-top:2mm;">'
            '<table style="width:' + str(2 * LW + CGAP) + 'mm;'
            'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
            + ''.join(rows_html) +
            '</table></div>'
            '</body></html>'
        )

        return html, PW, page_h

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
                '--page-width',    str(page_w) + 'mm',
                '--page-height',   str(page_h) + 'mm',
                '--margin-top',    '2mm',
                '--margin-bottom', '2mm',
                '--margin-left',   '0',
                '--margin-right',  '0',
                '--disable-smart-shrinking',
                '--zoom', '1',
                '--dpi', '203',
                '--no-stop-slow-scripts',
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