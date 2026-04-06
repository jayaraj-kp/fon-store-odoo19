# # from odoo import models, fields, api, _
# # from odoo.exceptions import UserError
# # import base64
# # import io
# # import os
# # import subprocess
# # import tempfile
# #
# #
# # class ProductLabelWizard(models.TransientModel):
# #     _name = 'product.label.wizard'
# #     _description = 'Product Label Printing Wizard'
# #
# #     product_tmpl_ids = fields.Many2many('product.template', string='Product Templates')
# #     product_ids = fields.Many2many('product.product', string='Product Variants')
# #     quantity = fields.Integer(string='Number of Labels per Product', default=1, required=True)
# #     show_mrp = fields.Boolean(string='Show MRP', default=True)
# #     show_qr = fields.Boolean(string='Show QR Code', default=True)
# #     show_label_code = fields.Boolean(string='Show Label Code', default=True)
# #
# #     # ── QR generator ──────────────────────────────────────────────────────────
# #
# #     def _make_qr_base64(self, value):
# #         try:
# #             import qrcode
# #             qr = qrcode.QRCode(
# #                 version=1,
# #                 error_correction=qrcode.constants.ERROR_CORRECT_L,
# #                 box_size=8,
# #                 border=1,
# #             )
# #             qr.add_data(value or 'LABEL')
# #             qr.make(fit=True)
# #             img = qr.make_image(fill_color='black', back_color='white')
# #             buf = io.BytesIO()
# #             img.save(buf, format='PNG')
# #             return base64.b64encode(buf.getvalue()).decode('ascii')
# #         except Exception:
# #             return (
# #                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
# #                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
# #             )
# #
# #     # ── Product / label helpers ───────────────────────────────────────────────
# #
# #     def _get_products(self):
# #         products = self.env['product.product']
# #         if self.product_ids:
# #             products |= self.product_ids
# #         if self.product_tmpl_ids:
# #             for tmpl in self.product_tmpl_ids:
# #                 products |= tmpl.product_variant_ids
# #         return products
# #
# #     def _get_label_list(self):
# #         products = self._get_products()
# #         label_list = []
# #         for product in products:
# #             tmpl = product.product_tmpl_id
# #             label_code = (getattr(tmpl, 'label_code', None) or
# #                           product.default_code or '')
# #             mrp = int(tmpl.list_price or 0)
# #             qr_value = (product.barcode or product.default_code or
# #                         tmpl.name or str(product.id))
# #             qr_b64 = self._make_qr_base64(qr_value)
# #             for _i in range(self.quantity):
# #                 label_list.append({
# #                     'name': tmpl.name or '',
# #                     'label_code': label_code,
# #                     'mrp': mrp,
# #                     'qr_b64': qr_b64,
# #                 })
# #         return label_list
# #
# #     # ── HTML builder ──────────────────────────────────────────────────────────
# #
# #     def _build_html(self, label_list):
# #         """
# #         GP-1125T roll: 152mm wide, labels feed horizontally.
# #
# #         Each label = two stacked cells (solid outer border, dashed divider):
# #         ┌──────────────────────────┐
# #         │   [QR]   KC110           │  top cell  (QR_H mm tall)
# #         ├╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
# #         │  KEYCHAIN 110            │  bottom cell (BOT_H mm tall)
# #         │  MRP Rs. 110             │
# #         └──────────────────────────┘
# #
# #         2 labels per row, side by side.
# #
# #         Page width  = 152mm  (full roll width)
# #         Page height = num_rows × (QR_H + BOT_H + ROW_GAP) + top/bottom margin
# #
# #         wkhtmltopdf flags:
# #           --page-width  152mm
# #           --page-height <calculated>mm
# #           --margin-*    0            (we control all spacing in HTML)
# #           --disable-smart-shrinking  (critical — prevents auto-scale)
# #           --zoom 1
# #           --dpi 203
# #         """
# #
# #         # ── Dimensions (all in mm) ──────────────────────────────────────────
# #         LW      = 65    # label width
# #         QR_H    = 26    # top cell height  (QR area)
# #         BOT_H   = 28    # bottom cell height (name/MRP)
# #         LH      = QR_H + BOT_H   # 53mm total per label
# #         QR_SIZE = 18    # QR image size
# #         COL_GAP = 66 # gap between 2 label columns
# #         ROW_GAP = 4     # gap between label rows
# #         L_MAR   = 17  # fixed left margin
# #         PW      = 160   # page/roll width mm (wider to fit the gap)
# #
# #         def _name_font_size(name):
# #             """Return font-size (pt) that keeps the product name within the label."""
# #             n = len(name or '')
# #             if n <= 10:
# #                 return 20
# #             elif n <= 15:
# #                 return 16
# #             elif n <= 22:
# #                 return 13
# #             else:
# #                 return 10
# #
# #         def _code_font_size(code):
# #             """Return font-size (pt) for the label code."""
# #             n = len(code or '')
# #             if n <= 6:
# #                 return 14
# #             elif n <= 10:
# #                 return 11
# #             else:
# #                 return 9
# #
# #         def one_label(lbl):
# #             # ── Top cell: QR left-aligned, label code below QR ──
# #             qr_html = ''
# #             if self.show_qr:
# #                 qr_html = (
# #                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
# #                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
# #                     'display:block;margin:0 auto;" alt=""/>'
# #                 )
# #
# #             code_html = ''
# #             if self.show_label_code and lbl.get('label_code'):
# #                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
# #                 code_html = (
# #                     '<div style="'
# #                     'text-align:center;'
# #                     'font-size:' + code_fs + ';font-weight:bold;'
# #                     'letter-spacing:0.3mm;'
# #                     'margin-top:1mm;'
# #                     'word-break:break-all;'
# #                     'overflow:hidden;'
# #                     '">'
# #                     + lbl['label_code'] +
# #                     '</div>'
# #                 )
# #
# #             top_cell = (
# #                 '<tr><td style="'
# #                 'height:' + str(QR_H) + 'mm;'
# #                 'padding:3mm 1mm 1mm 5mm;'
# #                 'vertical-align:top;'
# #                 'border-bottom:1.5px dashed #aaa;'
# #                 '">'
# #                 + qr_html + code_html +
# #                 '</td></tr>'
# #             )
# #
# #             # ── Bottom cell: product name + MRP ──
# #             name      = lbl['name'] or ''
# #             name_fs   = str(_name_font_size(name)) + 'pt'
# #
# #             mrp_html = ''
# #             if self.show_mrp:
# #                 mrp_html = (
# #                     '<div style="font-size:11pt;padding-left:6mm;margin-top:1mm;">'
# #                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
# #                 )
# #
# #             bot_cell = (
# #                 '<tr><td style="'
# #                 'height:' + str(BOT_H) + 'mm;'
# #                 'padding-bottom:3mm;'
# #                 'padding-left:12mm;'
# #                 'padding-right:2mm;'
# #                 'vertical-align:bottom;'
# #                 'overflow:hidden;'
# #                 '">'
# #                 '<div style="'
# #                 'font-size:' + name_fs + ';'
# #                 'font-weight:bold;'
# #                 'text-transform:uppercase;'
# #                 'word-break:break-word;'
# #                 'word-wrap:break-word;'
# #                 'white-space:normal;'
# #                 'line-height:1.15;'
# #                 'overflow:hidden;'
# #                 '">'
# #                 + name + '</div>'
# #                 + mrp_html +
# #                 '</td></tr>'
# #             )
# #
# #             return (
# #                 '<table style="'
# #                 'border-collapse:collapse;'
# #                 'width:' + str(LW) + 'mm;'
# #                 'border:1.5px solid #888;'
# #                 'border-radius:3mm;'
# #                 'background:white;'
# #                 'table-layout:fixed;">'
# #                 + top_cell + bot_cell +
# #                 '</table>'
# #             )
# #
# #         # ── Build pages: 2 labels per page (1 pair per page) ───────────────
# #         # Each page = exactly 1 row of 2 labels.
# #         # This means: if user selects 4 labels → 2 pages in PDF.
# #         # Browser prints all pages with Copies=1 → all labels print correctly.
# #         # No need to change Copies in browser print dialog.
# #
# #         page_h = 2 + LH + ROW_GAP + 2   # fixed: 1 row per page
# #
# #         pages_html = []
# #         i = 0
# #         while i < len(label_list):
# #             left  = label_list[i]
# #             right = label_list[i + 1] if (i + 1) < len(label_list) else None
# #             i += 2
# #
# #             row = (
# #                 '<tr>'
# #                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
# #                 + one_label(left) + '</td>'
# #                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
# #                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
# #                 + (one_label(right) if right else '') + '</td>'
# #                 '</tr>'
# #             )
# #
# #             pages_html.append(
# #                 '<div style="'
# #                 'width:' + str(PW) + 'mm;'
# #                 'height:' + str(page_h) + 'mm;'
# #                 'padding-top:2mm;'
# #                 'padding-left:' + str(L_MAR) + 'mm;'
# #                 'page-break-after:always;'
# #                 'box-sizing:border-box;'
# #                 '">'
# #                 '<table style="'
# #                 'width:' + str(2 * LW + COL_GAP) + 'mm;'
# #                 'border-collapse:separate;'
# #                 'border-spacing:0;'
# #                 'table-layout:fixed;">'
# #                 + row +
# #                 '</table>'
# #                 '</div>'
# #             )
# #
# #         html = (
# #             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
# #             '<style>'
# #             '* { margin:0; padding:0; box-sizing:border-box; }'
# #             'html, body {'
# #             '  font-family: Arial, Helvetica, sans-serif;'
# #             '  background: white;'
# #             '  width: ' + str(PW) + 'mm;'
# #             '}'
# #             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
# #             '</style></head>'
# #             '<body>'
# #             + ''.join(pages_html) +
# #             '</body></html>'
# #         )
# #
# #         return html, PW, page_h
# #
# #     # ── Print action ──────────────────────────────────────────────────────────
# #
# #     def action_print_labels(self):
# #         self.ensure_one()
# #         products = self._get_products()
# #         if not products:
# #             raise UserError(_('Please select at least one product.'))
# #
# #         label_list = self._get_label_list()
# #         html_content, page_w, page_h = self._build_html(label_list)
# #
# #         html_path = pdf_path = None
# #         try:
# #             with tempfile.NamedTemporaryFile(
# #                     suffix='.html', delete=False,
# #                     mode='w', encoding='utf-8') as fh:
# #                 fh.write(html_content)
# #                 html_path = fh.name
# #
# #             pdf_path = html_path.replace('.html', '.pdf')
# #
# #             cmd = [
# #                 'wkhtmltopdf',
# #                 # ── Page size: exactly the roll width × content height ──
# #                 '--page-width',     str(page_w) + 'mm',
# #                 '--page-height',    str(page_h) + 'mm',
# #                 # ── Zero margins (all spacing is in the HTML) ──
# #                 '--margin-top',     '0',
# #                 '--margin-bottom',  '0',
# #                 '--margin-left',    '0',
# #                 '--margin-right',   '0',
# #                 # ── Critical: prevent wkhtmltopdf from rescaling content ──
# #                 '--disable-smart-shrinking',
# #                 '--zoom',           '1',
# #                 '--dpi',            '203',
# #                 '--no-stop-slow-scripts',
# #                 '--encoding',       'UTF-8',
# #                 html_path,
# #                 pdf_path,
# #             ]
# #             result = subprocess.run(cmd, capture_output=True)
# #
# #             if result.returncode not in (0, 1) or not os.path.exists(pdf_path):
# #                 err = result.stderr.decode('utf-8', errors='replace')
# #                 raise UserError(
# #                     _('wkhtmltopdf failed (exit %s):\n%s')
# #                     % (result.returncode, err)
# #                 )
# #
# #             with open(pdf_path, 'rb') as f:
# #                 pdf_data = f.read()
# #
# #         finally:
# #             for p in (html_path, pdf_path):
# #                 if p and os.path.exists(p):
# #                     try:
# #                         os.unlink(p)
# #                     except Exception:
# #                         pass
# #
# #         attachment = self.env['ir.attachment'].create({
# #             'name': 'Product_Labels.pdf',
# #             'type': 'binary',
# #             'datas': base64.b64encode(pdf_data),
# #             'mimetype': 'application/pdf',
# #             'res_model': self._name,
# #             'res_id': self.id,
# #         })
# #
# #         pdf_url = '/web/content/' + str(attachment.id)
# #         products = self._get_products()
# #         product_names = ', '.join(products.mapped('name'))
# #         record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')
# #
# #         return {
# #             'type': 'ir.actions.client',
# #             'tag': 'product_label_print.open_print_dialog',
# #             'params': {
# #                 'pdf_url':       pdf_url,
# #                 'record_name':   record_name,
# #                 'label_qty':     self.quantity,
# #                 'product_count': len(products),
# #             },
# #         }
#
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
#     show_mrp = fields.Boolean(string='Show MRP', default=True)
#     show_qr = fields.Boolean(string='Show QR Code', default=True)
#     show_label_code = fields.Boolean(string='Show Label Code', default=True)
#     label_type = fields.Selection([
#         ('large', 'Large Label (65×54mm) — GP-1125T Roll'),
#         ('small', 'Small Label (25×15mm)'),
#     ], string='Label Size', default='large', required=True)
#
#     # ── QR generator ──────────────────────────────────────────────────────────
#
#     def _make_qr_base64(self, value):
#         try:
#             import qrcode
#             qr = qrcode.QRCode(
#                 version=1,
#                 error_correction=qrcode.constants.ERROR_CORRECT_L,
#                 box_size=8,
#                 border=1,
#             )
#             qr.add_data(value or 'LABEL')
#             qr.make(fit=True)
#             img = qr.make_image(fill_color='black', back_color='white')
#             buf = io.BytesIO()
#             img.save(buf, format='PNG')
#             return base64.b64encode(buf.getvalue()).decode('ascii')
#         except Exception:
#             return (
#                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
#                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
#             )
#
#     # ── Product / label helpers ───────────────────────────────────────────────
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
#     # ── LARGE label HTML builder (65×54mm, GP-1125T roll) ────────────────────
#
#     def _build_html_large(self, label_list):
#         LW      = 65
#         QR_H    = 26
#         BOT_H   = 28
#         LH      = QR_H + BOT_H
#         QR_SIZE = 18
#         COL_GAP = 66
#         ROW_GAP = 4
#         L_MAR   = 17
#         PW      = 160
#
#         def _name_font_size(name):
#             n = len(name or '')
#             if n <= 10:   return 20
#             elif n <= 15: return 16
#             elif n <= 22: return 13
#             else:         return 10
#
#         def _code_font_size(code):
#             n = len(code or '')
#             if n <= 6:    return 18
#             elif n <= 10: return 15
#             else:         return 12
#
#         def one_label(lbl):
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#
#             code_html = ''
#             if self.show_label_code and lbl.get('label_code'):
#                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
#                 code_html = (
#                     '<div style="text-align:center;font-size:' + code_fs + ';'
#                     'font-weight:bold;letter-spacing:0.3mm;margin-top:1mm;'
#                     'word-break:break-all;overflow:hidden;">'
#                     + lbl['label_code'] + '</div>'
#                 )
#
#             top_cell = (
#                 '<tr><td style="height:' + str(QR_H) + 'mm;'
#                 'padding:3mm 1mm 1mm 5mm;vertical-align:top;'
#                 'border-bottom:1.5px dashed #aaa;">'
#                 + qr_html + code_html + '</td></tr>'
#             )
#
#             name    = lbl['name'] or ''
#             name_fs = str(_name_font_size(name)) + 'pt'
#             mrp_html = ''
#             if self.show_mrp:
#                 mrp_html = (
#                     '<div style="font-size:11pt;padding-left:6mm;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             bot_cell = (
#                 '<tr><td style="height:' + str(BOT_H) + 'mm;'
#                 'padding-bottom:3mm;padding-left:4mm;padding-right:2mm;'
#                 'vertical-align:bottom;overflow:hidden;">'
#                 '<div style="font-size:' + name_fs + ';font-weight:bold;'
#                 'text-transform:uppercase;word-break:break-word;'
#                 'word-wrap:break-word;white-space:normal;line-height:1.15;'
#                 'overflow:hidden;">'
#                 + name + '</div>' + mrp_html + '</td></tr>'
#             )
#
#             return (
#                 '<table style="border-collapse:collapse;width:' + str(LW) + 'mm;'
#                 'border:1.5px solid #888;border-radius:3mm;background:white;'
#                 'table-layout:fixed;">'
#                 + top_cell + bot_cell + '</table>'
#             )
#
#         page_h = 2 + LH + ROW_GAP + 2
#         pages_html = []
#         i = 0
#         while i < len(label_list):
#             left  = label_list[i]
#             right = label_list[i + 1] if (i + 1) < len(label_list) else None
#             i += 2
#
#             row = (
#                 '<tr>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
#                 'padding-top:2mm;padding-left:' + str(L_MAR) + 'mm;'
#                 'page-break-after:always;box-sizing:border-box;">'
#                 '<table style="width:' + str(2 * LW + COL_GAP) + 'mm;'
#                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
#                 + row + '</table></div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             "  font-family: 'Arial Narrow', 'Liberation Sans', Arial, sans-serif;"
#             '  background: white;'
#             '  width: ' + str(PW) + 'mm;'
#             '}'
#             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW, page_h
#
#     # ── SMALL label HTML builder (25×15mm, 2 per row) ─────────────────────────
#
#     def _build_html_small(self, label_list):
#         """
#         Small label: 25mm wide × 15mm tall
#         Layout (landscape):
#         ┌─────────┬────────────────┐
#         │  [QR]   │  PRODUCT NAME  │
#         │  KC150  │  MRP Rs. 150   │
#         └─────────┴────────────────┘
#         2 labels per row.
#         """
#         LW      = 25    # label width mm
#         LH      = 15    # label height mm
#         QR_SIZE = 9     # QR image size mm
#         L_COL   = 11    # left column width (QR side)
#         R_COL   = 13    # right column width (text side)
#         COL_GAP = 4     # gap between 2 label columns
#         L_MAR   = 2     # left margin
#         PW      = 2 * LW + COL_GAP + 2 * L_MAR  # ~58mm page width
#
#         def _name_font_size(name):
#             n = len(name or '')
#             if n <= 8:    return 7
#             elif n <= 14: return 6
#             else:         return 5
#
#         def _code_font_size(code):
#             n = len(code or '')
#             if n <= 6:    return 6
#             elif n <= 10: return 5
#             else:         return 4
#
#         def one_label(lbl):
#             # ── QR column ──
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#
#             code_html = ''
#             if self.show_label_code and lbl.get('label_code'):
#                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
#                 code_html = (
#                     '<div style="text-align:center;font-size:' + code_fs + ';'
#                     'font-weight:bold;margin-top:0.5mm;word-break:break-all;">'
#                     + lbl['label_code'] + '</div>'
#                 )
#
#             left_col = (
#                 '<td style="width:' + str(L_COL) + 'mm;'
#                 'vertical-align:middle;text-align:center;'
#                 'padding:1mm 0.5mm;">'
#                 + qr_html + code_html + '</td>'
#             )
#
#             # ── Text column ──
#             name    = lbl['name'] or ''
#             name_fs = str(_name_font_size(name)) + 'pt'
#
#             mrp_html = ''
#             if self.show_mrp:
#                 mrp_html = (
#                     '<div style="font-size:5pt;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             right_col = (
#                 '<td style="width:' + str(R_COL) + 'mm;'
#                 'vertical-align:bottom;'
#                 'padding:1mm 1mm 1.5mm 1mm;overflow:hidden;">'
#                 '<div style="font-size:' + name_fs + ';font-weight:bold;'
#                 'text-transform:uppercase;word-break:break-word;'
#                 'word-wrap:break-word;white-space:normal;line-height:1.1;">'
#                 + name + '</div>'
#                 + mrp_html + '</td>'
#             )
#
#             # Divider line between QR and text
#             divider = (
#                 '<td style="width:0;border-left:1px dashed #aaa;padding:0;"></td>'
#             )
#
#             return (
#                 '<table style="border-collapse:collapse;'
#                 'width:' + str(LW) + 'mm;height:' + str(LH) + 'mm;'
#                 'border:1.5px solid #888;border-radius:2mm;background:white;'
#                 'table-layout:fixed;">'
#                 '<tr>' + left_col + divider + right_col + '</tr>'
#                 '</table>'
#             )
#
#         page_h = LH + 2    # 1 row per page + tiny margin
#         pages_html = []
#         i = 0
#         while i < len(label_list):
#             left  = label_list[i]
#             right = label_list[i + 1] if (i + 1) < len(label_list) else None
#             i += 2
#
#             row = (
#                 '<tr>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
#                 'padding-top:1mm;padding-left:' + str(L_MAR) + 'mm;'
#                 'page-break-after:always;box-sizing:border-box;">'
#                 '<table style="width:' + str(2 * LW + COL_GAP) + 'mm;'
#                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
#                 + row + '</table></div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             "  font-family: 'Arial Narrow', 'Liberation Sans', Arial, sans-serif;"
#             '  background: white;'
#             '  width: ' + str(PW) + 'mm;'
#             '}'
#             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW, page_h
#
#     # ── Print action ──────────────────────────────────────────────────────────
#
#     def action_print_labels(self):
#         self.ensure_one()
#         products = self._get_products()
#         if not products:
#             raise UserError(_('Please select at least one product.'))
#
#         label_list = self._get_label_list()
#
#         if self.label_type == 'small':
#             html_content, page_w, page_h = self._build_html_small(label_list)
#         else:
#             html_content, page_w, page_h = self._build_html_large(label_list)
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
#                 '--page-width',    str(page_w) + 'mm',
#                 '--page-height',   str(page_h) + 'mm',
#                 '--margin-top',    '0',
#                 '--margin-bottom', '0',
#                 '--margin-left',   '0',
#                 '--margin-right',  '0',
#                 '--disable-smart-shrinking',
#                 '--zoom',          '1',
#                 '--dpi',           '203',
#                 '--no-stop-slow-scripts',
#                 '--encoding',      'UTF-8',
#                 html_path,
#                 pdf_path,
#             ]
#             result = subprocess.run(cmd, capture_output=True)
#
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
#         pdf_url = '/web/content/' + str(attachment.id)
#         products = self._get_products()
#         product_names = ', '.join(products.mapped('name'))
#         record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'product_label_print.open_print_dialog',
#             'params': {
#                 'pdf_url':       pdf_url,
#                 'record_name':   record_name,
#                 'label_qty':     self.quantity,
#                 'product_count': len(products),
#             },
#         }

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
#     show_mrp = fields.Boolean(string='Show MRP', default=True)
#     show_qr = fields.Boolean(string='Show QR Code', default=True)
#     show_label_code = fields.Boolean(string='Show Label Code', default=True)
#
#     # ── QR generator ──────────────────────────────────────────────────────────
#
#     def _make_qr_base64(self, value):
#         try:
#             import qrcode
#             qr = qrcode.QRCode(
#                 version=1,
#                 error_correction=qrcode.constants.ERROR_CORRECT_L,
#                 box_size=8,
#                 border=1,
#             )
#             qr.add_data(value or 'LABEL')
#             qr.make(fit=True)
#             img = qr.make_image(fill_color='black', back_color='white')
#             buf = io.BytesIO()
#             img.save(buf, format='PNG')
#             return base64.b64encode(buf.getvalue()).decode('ascii')
#         except Exception:
#             return (
#                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
#                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
#             )
#
#     # ── Product / label helpers ───────────────────────────────────────────────
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
#     # ── HTML builder ──────────────────────────────────────────────────────────
#
#     def _build_html(self, label_list):
#         """
#         GP-1125T roll: 152mm wide, labels feed horizontally.
#
#         Each label = two stacked cells (solid outer border, dashed divider):
#         ┌──────────────────────────┐
#         │   [QR]   KC110           │  top cell  (QR_H mm tall)
#         ├╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
#         │  KEYCHAIN 110            │  bottom cell (BOT_H mm tall)
#         │  MRP Rs. 110             │
#         └──────────────────────────┘
#
#         2 labels per row, side by side.
#
#         Page width  = 152mm  (full roll width)
#         Page height = num_rows × (QR_H + BOT_H + ROW_GAP) + top/bottom margin
#
#         wkhtmltopdf flags:
#           --page-width  152mm
#           --page-height <calculated>mm
#           --margin-*    0            (we control all spacing in HTML)
#           --disable-smart-shrinking  (critical — prevents auto-scale)
#           --zoom 1
#           --dpi 203
#         """
#
#         # ── Dimensions (all in mm) ──────────────────────────────────────────
#         LW      = 65    # label width
#         QR_H    = 26    # top cell height  (QR area)
#         BOT_H   = 28    # bottom cell height (name/MRP)
#         LH      = QR_H + BOT_H   # 53mm total per label
#         QR_SIZE = 18    # QR image size
#         COL_GAP = 66 # gap between 2 label columns
#         ROW_GAP = 4     # gap between label rows
#         L_MAR   = 17  # fixed left margin
#         PW      = 160   # page/roll width mm (wider to fit the gap)
#
#         def _name_font_size(name):
#             """Return font-size (pt) that keeps the product name within the label."""
#             n = len(name or '')
#             if n <= 10:
#                 return 20
#             elif n <= 15:
#                 return 16
#             elif n <= 22:
#                 return 13
#             else:
#                 return 10
#
#         def _code_font_size(code):
#             """Return font-size (pt) for the label code."""
#             n = len(code or '')
#             if n <= 6:
#                 return 14
#             elif n <= 10:
#                 return 11
#             else:
#                 return 9
#
#         def one_label(lbl):
#             # ── Top cell: QR left-aligned, label code below QR ──
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#
#             code_html = ''
#             if self.show_label_code and lbl.get('label_code'):
#                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
#                 code_html = (
#                     '<div style="'
#                     'text-align:center;'
#                     'font-size:' + code_fs + ';font-weight:bold;'
#                     'letter-spacing:0.3mm;'
#                     'margin-top:1mm;'
#                     'word-break:break-all;'
#                     'overflow:hidden;'
#                     '">'
#                     + lbl['label_code'] +
#                     '</div>'
#                 )
#
#             top_cell = (
#                 '<tr><td style="'
#                 'height:' + str(QR_H) + 'mm;'
#                 'padding:3mm 1mm 1mm 5mm;'
#                 'vertical-align:top;'
#                 'border-bottom:1.5px dashed #aaa;'
#                 '">'
#                 + qr_html + code_html +
#                 '</td></tr>'
#             )
#
#             # ── Bottom cell: product name + MRP ──
#             name      = lbl['name'] or ''
#             name_fs   = str(_name_font_size(name)) + 'pt'
#
#             mrp_html = ''
#             if self.show_mrp:
#                 mrp_html = (
#                     '<div style="font-size:11pt;padding-left:6mm;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             bot_cell = (
#                 '<tr><td style="'
#                 'height:' + str(BOT_H) + 'mm;'
#                 'padding-bottom:3mm;'
#                 'padding-left:12mm;'
#                 'padding-right:2mm;'
#                 'vertical-align:bottom;'
#                 'overflow:hidden;'
#                 '">'
#                 '<div style="'
#                 'font-size:' + name_fs + ';'
#                 'font-weight:bold;'
#                 'text-transform:uppercase;'
#                 'word-break:break-word;'
#                 'word-wrap:break-word;'
#                 'white-space:normal;'
#                 'line-height:1.15;'
#                 'overflow:hidden;'
#                 '">'
#                 + name + '</div>'
#                 + mrp_html +
#                 '</td></tr>'
#             )
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(LW) + 'mm;'
#                 'border:1.5px solid #888;'
#                 'border-radius:3mm;'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 + top_cell + bot_cell +
#                 '</table>'
#             )
#
#         # ── Build pages: 2 labels per page (1 pair per page) ───────────────
#         # Each page = exactly 1 row of 2 labels.
#         # This means: if user selects 4 labels → 2 pages in PDF.
#         # Browser prints all pages with Copies=1 → all labels print correctly.
#         # No need to change Copies in browser print dialog.
#
#         page_h = 2 + LH + ROW_GAP + 2   # fixed: 1 row per page
#
#         pages_html = []
#         i = 0
#         while i < len(label_list):
#             left  = label_list[i]
#             right = label_list[i + 1] if (i + 1) < len(label_list) else None
#             i += 2
#
#             row = (
#                 '<tr>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="'
#                 'width:' + str(PW) + 'mm;'
#                 'height:' + str(page_h) + 'mm;'
#                 'padding-top:2mm;'
#                 'padding-left:' + str(L_MAR) + 'mm;'
#                 'page-break-after:always;'
#                 'box-sizing:border-box;'
#                 '">'
#                 '<table style="'
#                 'width:' + str(2 * LW + COL_GAP) + 'mm;'
#                 'border-collapse:separate;'
#                 'border-spacing:0;'
#                 'table-layout:fixed;">'
#                 + row +
#                 '</table>'
#                 '</div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             '  font-family: Arial, Helvetica, sans-serif;'
#             '  background: white;'
#             '  width: ' + str(PW) + 'mm;'
#             '}'
#             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
#             '</style></head>'
#             '<body>'
#             + ''.join(pages_html) +
#             '</body></html>'
#         )
#
#         return html, PW, page_h
#
#     # ── Print action ──────────────────────────────────────────────────────────
#
#     def action_print_labels(self):
#         self.ensure_one()
#         products = self._get_products()
#         if not products:
#             raise UserError(_('Please select at least one product.'))
#
#         label_list = self._get_label_list()
#         html_content, page_w, page_h = self._build_html(label_list)
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
#                 # ── Page size: exactly the roll width × content height ──
#                 '--page-width',     str(page_w) + 'mm',
#                 '--page-height',    str(page_h) + 'mm',
#                 # ── Zero margins (all spacing is in the HTML) ──
#                 '--margin-top',     '0',
#                 '--margin-bottom',  '0',
#                 '--margin-left',    '0',
#                 '--margin-right',   '0',
#                 # ── Critical: prevent wkhtmltopdf from rescaling content ──
#                 '--disable-smart-shrinking',
#                 '--zoom',           '1',
#                 '--dpi',            '203',
#                 '--no-stop-slow-scripts',
#                 '--encoding',       'UTF-8',
#                 html_path,
#                 pdf_path,
#             ]
#             result = subprocess.run(cmd, capture_output=True)
#
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
#         pdf_url = '/web/content/' + str(attachment.id)
#         products = self._get_products()
#         product_names = ', '.join(products.mapped('name'))
#         record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'product_label_print.open_print_dialog',
#             'params': {
#                 'pdf_url':       pdf_url,
#                 'record_name':   record_name,
#                 'label_qty':     self.quantity,
#                 'product_count': len(products),
#             },
#         }

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
#     show_mrp = fields.Boolean(string='Show MRP', default=True)
#     show_qr = fields.Boolean(string='Show QR Code', default=True)
#     show_label_code = fields.Boolean(string='Show Label Code', default=True)
#
#     # ── QR generator ──────────────────────────────────────────────────────────
#
#     def _make_qr_base64(self, value):
#         try:
#             import qrcode
#             qr = qrcode.QRCode(
#                 version=1,
#                 error_correction=qrcode.constants.ERROR_CORRECT_L,
#                 box_size=8,
#                 border=1,
#             )
#             qr.add_data(value or 'LABEL')
#             qr.make(fit=True)
#             img = qr.make_image(fill_color='black', back_color='white')
#             buf = io.BytesIO()
#             img.save(buf, format='PNG')
#             return base64.b64encode(buf.getvalue()).decode('ascii')
#         except Exception:
#             return (
#                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
#                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
#             )
#
#     # ── Product / label helpers ───────────────────────────────────────────────
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
#     # ── HTML builder ──────────────────────────────────────────────────────────
#
#     def _build_html(self, label_list):
#         """
#         GP-1125T roll: 152mm wide, labels feed horizontally.
#
#         Each label = two stacked cells (solid outer border, dashed divider):
#         ┌──────────────────────────┐
#         │   [QR]   KC110           │  top cell  (QR_H mm tall)
#         ├╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌┤
#         │  KEYCHAIN 110            │  bottom cell (BOT_H mm tall)
#         │  MRP Rs. 110             │
#         └──────────────────────────┘
#
#         2 labels per row, side by side.
#
#         Page width  = 152mm  (full roll width)
#         Page height = num_rows × (QR_H + BOT_H + ROW_GAP) + top/bottom margin
#
#         wkhtmltopdf flags:
#           --page-width  152mm
#           --page-height <calculated>mm
#           --margin-*    0            (we control all spacing in HTML)
#           --disable-smart-shrinking  (critical — prevents auto-scale)
#           --zoom 1
#           --dpi 203
#         """
#
#         # ── Dimensions (all in mm) ──────────────────────────────────────────
#         LW      = 65    # label width
#         QR_H    = 26    # top cell height  (QR area)
#         BOT_H   = 28    # bottom cell height (name/MRP)
#         LH      = QR_H + BOT_H   # 53mm total per label
#         QR_SIZE = 18    # QR image size
#         COL_GAP = 66 # gap between 2 label columns
#         ROW_GAP = 4     # gap between label rows
#         L_MAR   = 17  # fixed left margin
#         PW      = 160   # page/roll width mm (wider to fit the gap)
#
#         def _name_font_size(name):
#             """Return font-size (pt) that keeps the product name within the label."""
#             n = len(name or '')
#             if n <= 10:
#                 return 20
#             elif n <= 15:
#                 return 16
#             elif n <= 22:
#                 return 13
#             else:
#                 return 10
#
#         def _code_font_size(code):
#             """Return font-size (pt) for the label code."""
#             n = len(code or '')
#             if n <= 6:
#                 return 14
#             elif n <= 10:
#                 return 11
#             else:
#                 return 9
#
#         def one_label(lbl):
#             # ── Top cell: QR left-aligned, label code below QR ──
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#
#             code_html = ''
#             if self.show_label_code and lbl.get('label_code'):
#                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
#                 code_html = (
#                     '<div style="'
#                     'text-align:center;'
#                     'font-size:' + code_fs + ';font-weight:bold;'
#                     'letter-spacing:0.3mm;'
#                     'margin-top:1mm;'
#                     'word-break:break-all;'
#                     'overflow:hidden;'
#                     '">'
#                     + lbl['label_code'] +
#                     '</div>'
#                 )
#
#             top_cell = (
#                 '<tr><td style="'
#                 'height:' + str(QR_H) + 'mm;'
#                 'padding:3mm 1mm 1mm 5mm;'
#                 'vertical-align:top;'
#                 'border-bottom:1.5px dashed #aaa;'
#                 '">'
#                 + qr_html + code_html +
#                 '</td></tr>'
#             )
#
#             # ── Bottom cell: product name + MRP ──
#             name      = lbl['name'] or ''
#             name_fs   = str(_name_font_size(name)) + 'pt'
#
#             mrp_html = ''
#             if self.show_mrp:
#                 mrp_html = (
#                     '<div style="font-size:11pt;padding-left:6mm;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             bot_cell = (
#                 '<tr><td style="'
#                 'height:' + str(BOT_H) + 'mm;'
#                 'padding-bottom:3mm;'
#                 'padding-left:12mm;'
#                 'padding-right:2mm;'
#                 'vertical-align:bottom;'
#                 'overflow:hidden;'
#                 '">'
#                 '<div style="'
#                 'font-size:' + name_fs + ';'
#                 'font-weight:bold;'
#                 'text-transform:uppercase;'
#                 'word-break:break-word;'
#                 'word-wrap:break-word;'
#                 'white-space:normal;'
#                 'line-height:1.15;'
#                 'overflow:hidden;'
#                 '">'
#                 + name + '</div>'
#                 + mrp_html +
#                 '</td></tr>'
#             )
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(LW) + 'mm;'
#                 'border:1.5px solid #888;'
#                 'border-radius:3mm;'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 + top_cell + bot_cell +
#                 '</table>'
#             )
#
#         # ── Build pages: 2 labels per page (1 pair per page) ───────────────
#         # Each page = exactly 1 row of 2 labels.
#         # This means: if user selects 4 labels → 2 pages in PDF.
#         # Browser prints all pages with Copies=1 → all labels print correctly.
#         # No need to change Copies in browser print dialog.
#
#         page_h = 2 + LH + ROW_GAP + 2   # fixed: 1 row per page
#
#         pages_html = []
#         i = 0
#         while i < len(label_list):
#             left  = label_list[i]
#             right = label_list[i + 1] if (i + 1) < len(label_list) else None
#             i += 2
#
#             row = (
#                 '<tr>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="'
#                 'width:' + str(PW) + 'mm;'
#                 'height:' + str(page_h) + 'mm;'
#                 'padding-top:2mm;'
#                 'padding-left:' + str(L_MAR) + 'mm;'
#                 'page-break-after:always;'
#                 'box-sizing:border-box;'
#                 '">'
#                 '<table style="'
#                 'width:' + str(2 * LW + COL_GAP) + 'mm;'
#                 'border-collapse:separate;'
#                 'border-spacing:0;'
#                 'table-layout:fixed;">'
#                 + row +
#                 '</table>'
#                 '</div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             '  font-family: Arial, Helvetica, sans-serif;'
#             '  background: white;'
#             '  width: ' + str(PW) + 'mm;'
#             '}'
#             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
#             '</style></head>'
#             '<body>'
#             + ''.join(pages_html) +
#             '</body></html>'
#         )
#
#         return html, PW, page_h
#
#     # ── Print action ──────────────────────────────────────────────────────────
#
#     def action_print_labels(self):
#         self.ensure_one()
#         products = self._get_products()
#         if not products:
#             raise UserError(_('Please select at least one product.'))
#
#         label_list = self._get_label_list()
#         html_content, page_w, page_h = self._build_html(label_list)
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
#                 # ── Page size: exactly the roll width × content height ──
#                 '--page-width',     str(page_w) + 'mm',
#                 '--page-height',    str(page_h) + 'mm',
#                 # ── Zero margins (all spacing is in the HTML) ──
#                 '--margin-top',     '0',
#                 '--margin-bottom',  '0',
#                 '--margin-left',    '0',
#                 '--margin-right',   '0',
#                 # ── Critical: prevent wkhtmltopdf from rescaling content ──
#                 '--disable-smart-shrinking',
#                 '--zoom',           '1',
#                 '--dpi',            '203',
#                 '--no-stop-slow-scripts',
#                 '--encoding',       'UTF-8',
#                 html_path,
#                 pdf_path,
#             ]
#             result = subprocess.run(cmd, capture_output=True)
#
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
#         pdf_url = '/web/content/' + str(attachment.id)
#         products = self._get_products()
#         product_names = ', '.join(products.mapped('name'))
#         record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'product_label_print.open_print_dialog',
#             'params': {
#                 'pdf_url':       pdf_url,
#                 'record_name':   record_name,
#                 'label_qty':     self.quantity,
#                 'product_count': len(products),
#             },
#         }

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
    label_type = fields.Selection([
        ('large', 'Large Label (65×54mm) — GP-1125T Roll'),
        ('small', 'Small Label (25×15mm)'),
    ], string='Label Size', default='large', required=True)

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

    # ── LARGE label HTML builder (65×54mm, GP-1125T roll) ────────────────────

    def _build_html_large(self, label_list):
        LW      = 65
        QR_H    = 26
        BOT_H   = 28
        LH      = QR_H + BOT_H
        QR_SIZE = 18
        COL_GAP = 60
        ROW_GAP = 4
        L_MAR   = 13
        PW      = 160

        def _name_font_size(name):
            n = len(name or '')
            if n <= 10:   return 20
            elif n <= 15: return 16
            elif n <= 22: return 13
            else:         return 10

        def _code_font_size(code):
            n = len(code or '')
            if n <= 6:    return 18
            elif n <= 10: return 15
            else:         return 12

        def one_label(lbl):
            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
                    'display:block;margin:0 auto;" alt=""/>'
                )

            code_html = ''
            if self.show_label_code and lbl.get('label_code'):
                code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
                code_html = (
                    '<div style="text-align:center;font-size:' + code_fs + ';'
                    'font-weight:bold;letter-spacing:0.3mm;margin-top:1mm;'
                    'word-break:break-all;overflow:hidden;">'
                    + lbl['label_code'] + '</div>'
                )

            top_cell = (
                '<tr><td style="height:' + str(QR_H) + 'mm;'
                'padding:3mm 1mm 1mm 5mm;vertical-align:top;'
                'border-bottom:1.5px dashed #aaa;">'
                + qr_html + code_html + '</td></tr>'
            )

            name    = lbl['name'] or ''
            name_fs = str(_name_font_size(name)) + 'pt'
            mrp_html = ''
            if self.show_mrp:
                mrp_html = (
                    '<div style="font-size:14pt;padding-left:4mm;margin-top:1mm;">'
                    'MRP Rs. ' + str(lbl['mrp']) + '</div>'
                )

            bot_cell = (
                '<tr><td style="height:' + str(BOT_H) + 'mm;'
                'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;'
                'vertical-align:bottom;overflow:hidden;">'
                '<div style="font-size:' + name_fs + ';'
                'text-transform:uppercase;word-break:break-word;'
                'word-wrap:break-word;white-space:normal;line-height:2;'
                'overflow:hidden;">'
                + name + '</div>' + mrp_html + '</td></tr>'
            )

            return (
                '<table style="border-collapse:collapse;width:' + str(LW) + 'mm;'
                'border:1.5px solid #888;border-radius:3mm;background:white;'
                'table-layout:fixed;">'
                + top_cell + bot_cell + '</table>'
            )

        page_h = 2 + LH + ROW_GAP + 2
        pages_html = []
        i = 0
        while i < len(label_list):
            left  = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                '<tr>'
                '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
                + one_label(left) + '</td>'
                '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
                '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
                + (one_label(right) if right else '') + '</td>'
                '</tr>'
            )

            pages_html.append(
                '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
                'padding-top:2mm;padding-left:' + str(L_MAR) + 'mm;'
                'page-break-after:always;box-sizing:border-box;">'
                '<table style="width:' + str(2 * LW + COL_GAP) + 'mm;'
                'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
                + row + '</table></div>'
            )

        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<style>'
            '* { margin:0; padding:0; box-sizing:border-box; }'
            'html, body {'
            "  font-family: 'Arial Narrow', 'Liberation Sans', Arial, sans-serif;"
            '  background: white;'
            '  width: ' + str(PW) + 'mm;'
            '}'
            '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
            '</style></head><body>'
            + ''.join(pages_html)
            + '</body></html>'
        )
        return html, PW, page_h

    # ── SMALL label HTML builder — matches "for small" stock: 3.28in × 0.67in ──

    def _build_html_small(self, label_list):
        MM = 3.7795  # CSS px per mm  (96 dpi / 25.4)

        # ── Physical dimensions to match "for small (3.28 in x 0.67 in)" stock ──
        # Roll = 83.31mm wide  →  2 labels per row, each ~38mm wide
        # Feed = 17.02mm tall  →  label height
        LW_MM = 28.0  # each label width
        LH_MM = 13.0  # label height (= 0.67 in)
        QR_MM = 10.0  # QR image size
        QR_COL_MM = 13.0  # left column  (QR + code)
        NAME_COL_MM = 10.0  # middle column (product name, rotated)
        MRP_COL_MM = 5.0  # right column  (MRP, rotated)

        COL_GAP_MM = 4.0  # gap between the two labels
        L_MAR_MM = 30.0  # left margin
        PW_MM = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM  # = 83mm

        # ── px equivalents ────────────────────────────────────────────────────────
        LW = LW_MM * MM
        LH = LH_MM * MM
        QC = QR_COL_MM * MM
        NC = NAME_COL_MM * MM
        MC = MRP_COL_MM * MM
        PW = PW_MM * MM

        def px(mm):
            return str(round(mm * MM, 2)) + 'px'

        def _name_font(name):
            n = len(name or '')
            if n <= 8:
                return '7pt'
            elif n <= 14:
                return '6pt'
            else:
                return '5pt'

        def _code_font(code):
            n = len(code or '')
            if n <= 8:
                return '6pt'
            elif n <= 12:
                return '5pt'
            else:
                return '4pt'

        # ── Rotated-text cell helper ───────────────────────────────────────────────
        # The inner div is LH px wide × col_w px tall before rotation.
        # rotate(-90deg) makes it col_w px wide × LH px tall — fitting the cell.
        def rotated_cell(text, col_w_mm, font_size, extra_style=''):
            col_w = col_w_mm * MM
            shift = (LH - col_w) / 2.0
            inner = (
                    '<div style="'
                    'width:' + str(round(LH, 2)) + 'px;'
                                                   'height:' + str(round(col_w, 2)) + 'px;'
                                                                                      'display:flex;flex-direction:column;'
                                                                                      'align-items:center;justify-content:center;'
                                                                                      'overflow:hidden;'
                                                                                      'font-size:' + font_size + ';'
                                                                                                                 'font-weight:bold;'
                                                                                                                 'padding:1px 2px;'
                                                                                                                  'padding-left:5px;'
                    + extra_style +
                    'transform:rotate(-90deg);'
                    '-webkit-transform:rotate(-90deg);'
                    'transform-origin:50% 50%;'
                    '-webkit-transform-origin:50% 50%;'
                    'margin-top:' + str(round(-shift, 2)) + 'px;'
                                                            'margin-left:' + str(round(-shift, 2)) + 'px;'
                                                                                                     '">' + text + '</div>'
            )
            return (
                    '<td style="'
                    'width:' + str(round(col_w, 2)) + 'px;'
                                                      'height:' + str(round(LH, 2)) + 'px;'
                                                                                      'overflow:hidden;padding:0;'
                                                                                      'vertical-align:middle;text-align:center;">'
                    + inner + '</td>'
            )

        def one_label(lbl):
            name = lbl['name'] or ''
            code = lbl.get('label_code') or ''

            # ── Col 1: QR image + label code ─────────────────────────────────────
            qr_html = ''
            if self.show_qr:
                qr_html = (
                        '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                                                                             'style="width:' + px(
                    QR_MM) + ';height:' + px(QR_MM) + ';'
                                                      'display:block;margin:0 auto;" alt=""/>'
                )
            code_html = ''
            if self.show_label_code and code:
                code_html = (
                        '<div style="text-align:center;font-size:' + _code_font(code) + ';'
                                                                                        'font-weight:bold;margin-top:1px;white-space:nowrap;'
                                                                                        'overflow:hidden;width:' + str(
                    round(QC, 2)) + 'px;">'
                        + code + '</div>'
                )
            col1 = (
                    '<td style="width:' + str(round(QC, 2)) + 'px;'
                                                              'height:' + str(round(LH, 2)) + 'px;'
                                                                                              'vertical-align:middle;text-align:center;'
                                                                                              'padding:1px;overflow:hidden;">'
                    + qr_html + code_html + '</td>'
            )

            div1 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'

            # ── Col 2: Product name — rotated ─────────────────────────────────────
            def wrap_name(n, chars=6):
                words = n.split()
                lines, cur = [], ''
                for w in words:
                    if cur and len(cur) + 1 + len(w) > chars:
                        lines.append(cur);
                        cur = w
                    else:
                        cur = (cur + ' ' + w).strip()
                if cur: lines.append(cur)
                return '<br/>'.join(lines)

            col2 = rotated_cell(
                wrap_name(name.upper()),
                NAME_COL_MM,
                _name_font(name),
                extra_style=(
                    'text-transform:uppercase;'
                    'letter-spacing:0.2px;'
                    'white-space:normal;'
                    'word-break:break-word;'
                    'text-align:center;'
                    'line-height:1.2;'
                ),
            )

            div2 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'

            # ── Col 3: MRP — rotated ───────────────────────────────────────────────
            if self.show_mrp:
                col3 = rotated_cell(
                    'MRP Rs.' + str(lbl['mrp']),
                    MRP_COL_MM,
                    '5pt',
                    extra_style='white-space:nowrap;',
                )
            else:
                col3 = (
                        '<td style="width:' + str(round(MC, 2)) + 'px;'
                                                                  'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
                )

            return (
                    '<table style="'
                    'border-collapse:collapse;'
                    'width:' + str(round(LW, 2)) + 'px;'
                                                   'height:' + str(round(LH, 2)) + 'px;'
                                                                                   'border:1.5px solid #888;'
                                                                                   'border-radius:' + px(1.5) + ';'
                                                                                                                'background:white;'
                                                                                                                'table-layout:fixed;">'
                                                                                                                '<tr>' + col1 + div1 + col2 + div2 + col3 + '</tr>'
                                                                                                                                                            '</table>'
            )

        # ── Page layout: 1 row (2 labels) per page ────────────────────────────────
        GAP = COL_GAP_MM * MM
        MAR = L_MAR_MM * MM
        PH = (LH_MM + 1) * MM  # tiny 1mm top margin

        pages_html = []
        i = 0
        while i < len(label_list):
            left = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                    '<tr>'
                    '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
                    + one_label(left) + '</td>'
                                        '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>'
                                                                                   '<td style="width:' + str(
                round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
                    + (one_label(right) if right else '') + '</td>'
                                                            '</tr>'
            )

            pages_html.append(
                '<div style="'
                'width:' + str(round(PW, 2)) + 'px;'
                                               'height:' + str(round(PH, 2)) + 'px;'
                                                                               'padding-top:0.5mm;'
                                                                               'padding-left:' + str(
                    round(MAR, 2)) + 'px;'
                                     'page-break-after:always;'
                                     'box-sizing:border-box;">'
                                     '<table style="'
                                     'width:' + str(round(2 * LW + GAP, 2)) + 'px;'
                                                                              'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
                + row + '</table></div>'
            )

        html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
                '<style>'
                '* { margin:0; padding:0; box-sizing:border-box; }'
                'html, body {'
                "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
                '  background:white;'
                '}'
                '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 1) + 'mm; }'
                                                                                   '</style></head><body>'
                + ''.join(pages_html)
                + '</body></html>'
        )
        return html, PW_MM, LH_MM + 1

    # ── Print action ──────────────────────────────────────────────────────────

    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        label_list = self._get_label_list()

        if self.label_type == 'small':
            html_content, page_w, page_h = self._build_html_small(label_list)
        else:
            html_content, page_w, page_h = self._build_html_large(label_list)

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
                '--margin-top',    '0',
                '--margin-bottom', '0',
                '--margin-left',   '0',
                '--margin-right',  '0',
                '--disable-smart-shrinking',
                '--zoom',          '1',
                '--dpi',           '203',
                '--no-stop-slow-scripts',
                '--encoding',      'UTF-8',
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

        pdf_url = '/web/content/' + str(attachment.id)
        products = self._get_products()
        product_names = ', '.join(products.mapped('name'))
        record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')

        return {
            'type': 'ir.actions.client',
            'tag': 'product_label_print.open_print_dialog',
            'params': {
                'pdf_url':       pdf_url,
                'record_name':   record_name,
                'label_qty':     self.quantity,
                'product_count': len(products),
            },
        }