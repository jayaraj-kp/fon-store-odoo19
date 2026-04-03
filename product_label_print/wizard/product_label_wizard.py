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
    label_width_mm = fields.Integer(string='Label Width (mm)', default=75)
    label_height_mm = fields.Integer(string='Label Height (mm)', default=30)
    columns = fields.Selection(
        [('1', '1 Column'), ('2', '2 Columns')],
        string='Columns per Row', default='2', required=True,
    )
    show_mrp = fields.Boolean(string='Show MRP', default=True)
    show_qr = fields.Boolean(string='Show QR Code', default=True)
    show_label_code = fields.Boolean(string='Show Label Code', default=True)

    # ------------------------------------------------------------------
    # QR helper
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
    # Product helpers
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

    # ------------------------------------------------------------------
    # HTML builder
    #
    # Physical label stock: 75mm wide x 30mm tall each
    # Roll total width: 152mm = 2 labels (75mm each) + 2mm gap
    #
    # Layout per label:
    #
    #  ┌───────────────────────────────┐
    #  │ [QR 19x19mm] │(space)│ KC110 │  ← top 20mm
    #  ├───────────────────────────────┤
    #  │ PRODUCT NAME                  │  ← bottom 10mm
    #  │ MRP Rs  110                   │
    #  └───────────────────────────────┘
    #
    # ------------------------------------------------------------------
    def _build_label_html(self, label_list, col_count):
        css = """
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            html, body {
                font-family: Arial, Helvetica, sans-serif;
                background: white;
                width: 100%;
            }

            table.sheet {
                border-collapse: separate;
                border-spacing: 0;
                width: 100%;
                table-layout: fixed;
            }

            td.col-gap {
                width: 2mm;
                border: none;
                padding: 0;
            }

            tr.row-gap td {
                height: 1mm;
                border: none;
                padding: 0;
            }

            /* Each label: exactly 75mm wide, 30mm tall */
            td.label-cell {
                width: 75mm;
                height: 30mm;
                border: 1px solid #999;
                border-radius: 2mm;
                padding: 0;
                vertical-align: top;
                overflow: hidden;
            }

            table.inner {
                width: 75mm;
                height: 30mm;
                border-collapse: collapse;
                table-layout: fixed;
            }

            /* Top row: 20mm tall */
            td.top-section {
                width: 75mm;
                height: 20mm;
                padding: 0;
                vertical-align: top;
            }

            table.top-inner {
                width: 100%;
                height: 20mm;
                border-collapse: collapse;
                table-layout: fixed;
            }

            td.qr-cell {
                width: 20mm;
                height: 20mm;
                text-align: center;
                vertical-align: middle;
                padding: 0.5mm;
            }
            td.qr-cell img {
                width: 19mm;
                height: 19mm;
                display: block;
            }

            td.top-spacer {
                /* fills remaining width */
            }

            td.code-cell {
                width: 6mm;
                height: 20mm;
                text-align: center;
                vertical-align: middle;
                padding: 0;
            }
            .code-rotated {
                display: inline-block;
                writing-mode: vertical-lr;
                transform: rotate(180deg);
                font-size: 5pt;
                font-weight: bold;
                letter-spacing: 0.3pt;
                white-space: nowrap;
            }

            /* Bottom row: 10mm tall */
            td.bottom-section {
                width: 75mm;
                height: 10mm;
                vertical-align: middle;
                padding: 1mm 2mm;
                border-top: 0.3px solid #ccc;
            }
            .pname {
                display: block;
                font-size: 6pt;
                font-weight: bold;
                text-transform: uppercase;
                line-height: 1.3;
                white-space: nowrap;
                overflow: hidden;
            }
            .mrp-line {
                display: block;
                font-size: 5.5pt;
                margin-top: 0.2mm;
                white-space: nowrap;
            }
        </style>
        """

        rows = [label_list[i:i + col_count]
                for i in range(0, len(label_list), col_count)]

        html_rows = []
        for r_idx, row in enumerate(rows):
            cells = []
            for c_idx, lbl in enumerate(row):

                qr_html = ''
                if self.show_qr:
                    qr_html = '<img src="data:image/png;base64,{b64}" alt="QR"/>'.format(
                        b64=lbl['qr_b64'])

                code_html = ''
                if self.show_label_code and lbl.get('label_code'):
                    code_html = (
                        '<td class="code-cell">'
                        '<span class="code-rotated">{code}</span>'
                        '</td>'
                    ).format(code=lbl['label_code'])

                mrp_html = ''
                if self.show_mrp:
                    mrp_html = '<span class="mrp-line">MRP Rs&nbsp;&nbsp;{mrp}</span>'.format(
                        mrp=lbl['mrp'])

                cell = (
                    '<td class="label-cell">'
                      '<table class="inner">'
                        '<tr>'
                          '<td class="top-section">'
                            '<table class="top-inner">'
                              '<tr>'
                                '<td class="qr-cell">{qr}</td>'
                                '<td class="top-spacer"></td>'
                                '{code}'
                              '</tr>'
                            '</table>'
                          '</td>'
                        '</tr>'
                        '<tr>'
                          '<td class="bottom-section">'
                            '<span class="pname">{name}</span>'
                            '{mrp}'
                          '</td>'
                        '</tr>'
                      '</table>'
                    '</td>'
                ).format(qr=qr_html, code=code_html, name=lbl['name'], mrp=mrp_html)

                cells.append(cell)
                if c_idx < len(row) - 1:
                    cells.append('<td class="col-gap"></td>')

            html_rows.append('<tr>{}</tr>'.format(''.join(cells)))
            if r_idx < len(rows) - 1:
                html_rows.append(
                    '<tr class="row-gap"><td colspan="{n}"></td></tr>'.format(
                        n=(col_count * 2 - 1)))

        return (
            '<!DOCTYPE html>'
            '<html><head><meta charset="utf-8"/>{css}</head>'
            '<body><table class="sheet">{rows}</table></body>'
            '</html>'
        ).format(css=css, rows=''.join(html_rows))

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        col_count = int(self.columns)
        label_list = self._get_label_list()
        num_rows = (len(label_list) + col_count - 1) // col_count

        # GP-1125T roll is exactly 152mm wide = 2 x 75mm labels + 2mm gap
        # Height = rows x 30mm + row-gaps x 1mm
        if col_count == 2:
            page_w = 152
        else:
            page_w = 76   # 75mm label + 1mm breathing room

        page_h = (num_rows * 30) + max(0, (num_rows - 1) * 1)

        html_content = self._build_label_html(label_list, col_count)

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
                '--page-width',    '{}mm'.format(page_w),
                '--page-height',   '{}mm'.format(page_h),
                '--margin-top',    '0',
                '--margin-bottom', '0',
                '--margin-left',   '0',
                '--margin-right',  '0',
                '--disable-smart-shrinking',
                '--zoom', '1',
                '--dpi', '203',
                '--no-stop-slow-scripts',
                '--disable-external-links',
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
            'url': '/web/content/{}?download=true'.format(attachment.id),
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