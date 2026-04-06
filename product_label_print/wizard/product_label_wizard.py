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
#         COL_GAP = 60
#         ROW_GAP = 4
#         L_MAR   = 13
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
#                     '<div style="font-size:14pt;padding-left:4mm;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             bot_cell = (
#                 '<tr><td style="height:' + str(BOT_H) + 'mm;'
#                 'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;'
#                 'vertical-align:bottom;overflow:hidden;">'
#                 '<div style="font-size:' + name_fs + ';'
#                 'text-transform:uppercase;word-break:break-word;'
#                 'word-wrap:break-word;white-space:normal;line-height:2;'
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
#         MM = 3.7795
#
#         # ── Label dimensions ──────────────────────────────────────────────────
#         LW_MM       = 25.0
#         LH_MM       = 15.0
#         QR_MM       = 7.0
#         QR_COL_MM   = 12.0
#         NAME_COL_MM = 8.0
#         MRP_COL_MM  = 5.0
#
#         COL_GAP_MM = 4.0
#         L_MAR_MM   = 2.0
#         PW_MM      = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
#
#         LW = LW_MM  * MM
#         LH = LH_MM  * MM
#         QC = QR_COL_MM   * MM
#         MC = MRP_COL_MM  * MM
#         PW = PW_MM  * MM
#
#         def px(mm): return str(round(mm * MM, 2)) + 'px'
#
#         def _name_font(name):
#             n = len(name or '')
#             if n <= 8:    return '7pt'
#             elif n <= 14: return '6pt'
#             else:         return '5pt'
#
#         def _code_font(code):
#             n = len(code or '')
#             if n <= 8:    return '6pt'
#             elif n <= 12: return '5pt'
#             else:         return '4pt'
#
#         # ── Rotated-text helper ───────────────────────────────────────────────
#         # The rotated div natural size = LH wide x col_w tall.
#         # After rotate(-90deg) it becomes col_w wide x LH tall.
#         # justify-content:flex-end  →  text pushed to the BOTTOM of the column
#         # (which visually = the RIGHT side of the label, near the label edge)
#         def rotated_cell(text, col_w_mm, font_size, extra_style='', align='center'):
#             col_w = col_w_mm * MM
#             shift = (LH - col_w) / 2.0
#             transform = (
#                 'transform:rotate(-90deg);'
#                 '-webkit-transform:rotate(-90deg);'
#                 'transform-origin:50%% 50%%;'
#                 '-webkit-transform-origin:50%% 50%%;'
#             )
#             # justify-content controls vertical position BEFORE rotation.
#             # Before rotation the div is LH tall.
#             # 'flex-end' pushes content to the bottom of that LH height.
#             # After -90deg rotation, bottom-of-LH maps to the LEFT side of
#             # the label (the QR side), so we use 'flex-start' to push toward
#             # the label's bottom edge (right side before rotation).
#             justify = 'flex-start' if align == 'bottom' else 'center'
#             rotated_div = (
#                 '<div style="'
#                 'width:' + str(round(LH, 2)) + 'px;'
#                 'height:' + str(round(col_w, 2)) + 'px;'
#                 'display:flex;'
#                 'flex-direction:column;'
#                 'align-items:center;'
#                 'justify-content:' + justify + ';'
#                 'overflow:hidden;'
#                 'font-size:' + font_size + ';'
#                 'font-weight:bold;'
#                 'padding:1px 2px;'
#                 + extra_style +
#                 transform +
#                 'margin-top:' + str(round(-shift, 2)) + 'px;'
#                 'margin-left:' + str(round(-shift, 2)) + 'px;'
#                 '">' + text + '</div>'
#             )
#             return (
#                 '<td style="'
#                 'width:' + str(round(col_w, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'overflow:hidden;'
#                 'padding:0;'
#                 'vertical-align:middle;'
#                 'text-align:center;'
#                 '">'
#                 + rotated_div +
#                 '</td>'
#             )
#
#         def one_label(lbl):
#             name = lbl['name'] or ''
#             code = lbl.get('label_code') or ''
#
#             # ── Col 1: QR top, label code bottom ─────────────────────────────
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + px(QR_MM) + ';height:' + px(QR_MM) + ';'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#             code_html = ''
#             if self.show_label_code and code:
#                 code_html = (
#                     '<div style="text-align:center;font-size:' + _code_font(code) + ';'
#                     'font-weight:bold;margin-top:1px;white-space:nowrap;'
#                     'overflow:hidden;width:' + str(round(QC, 2)) + 'px;">'
#                     + code + '</div>'
#                 )
#             col1 = (
#                 '<td style="width:' + str(round(QC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;text-align:center;'
#                 'padding:1px;overflow:hidden;">'
#                 + qr_html + code_html +
#                 '</td>'
#             )
#
#             div1 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
#
#             # ── Col 2: Product name — rotated, pushed to bottom ───────────────
#             def wrap_name(n, chars_per_line=7):
#                 words = n.split()
#                 lines = []
#                 current = ''
#                 for w in words:
#                     if current and len(current) + 1 + len(w) > chars_per_line:
#                         lines.append(current)
#                         current = w
#                     else:
#                         current = (current + ' ' + w).strip()
#                 if current:
#                     lines.append(current)
#                 return '<br/>'.join(lines)
#
#             wrapped_name = wrap_name(name.upper())
#             col2 = rotated_cell(
#                 wrapped_name,
#                 NAME_COL_MM,
#                 _name_font(name),
#                 extra_style=(
#                     'text-transform:uppercase;'
#                     'letter-spacing:0.2px;'
#                     'white-space:normal;'
#                     'word-break:break-word;'
#                     'text-align:center;'
#                     'line-height:1.2;'
#                 ),
#                 align='bottom',
#             )
#
#             div2 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
#
#             # ── Col 3: MRP — rotated, pushed to bottom ────────────────────────
#             col3 = (
#                 '<td style="width:' + str(round(MC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
#             )
#             if self.show_mrp:
#                 mrp_text = 'MRP Rs.' + str(lbl['mrp'])
#                 col3 = rotated_cell(
#                     mrp_text,
#                     MRP_COL_MM,
#                     '5pt',
#                     extra_style='white-space:nowrap;',
#                     align='bottom',
#                 )
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(round(LW, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'border:1.5px solid #888;'
#                 'border-radius:' + px(2) + ';'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 '<tr>' + col1 + div1 + col2 + div2 + col3 + '</tr>'
#                 '</table>'
#             )
#
#         # ── Page layout: 2 labels per page ───────────────────────────────────
#         GAP = COL_GAP_MM * MM
#         MAR = L_MAR_MM   * MM
#         PH  = (LH_MM + 2) * MM
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
#                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="'
#                 'width:' + str(round(PW, 2)) + 'px;'
#                 'height:' + str(round(PH, 2)) + 'px;'
#                 'padding-top:' + str(round(1 * MM, 2)) + 'px;'
#                 'padding-left:' + str(round(MAR, 2)) + 'px;'
#                 'page-break-after:always;'
#                 'box-sizing:border-box;">'
#                 '<table style="'
#                 'width:' + str(round(2 * LW + GAP, 2)) + 'px;'
#                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
#                 + row + '</table></div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
#             '  background:white;'
#             '}'
#             '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW_MM, LH_MM + 2
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
#         COL_GAP = 60
#         ROW_GAP = 4
#         L_MAR   = 13
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
#                     '<div style="font-size:14pt;padding-left:4mm;margin-top:1mm;">'
#                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
#                 )
#
#             bot_cell = (
#                 '<tr><td style="height:' + str(BOT_H) + 'mm;'
#                 'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;'
#                 'vertical-align:bottom;overflow:hidden;">'
#                 '<div style="font-size:' + name_fs + ';'
#                 'text-transform:uppercase;word-break:break-word;'
#                 'word-wrap:break-word;white-space:normal;line-height:2;'
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
#     #
#     # Layout (label reads left-to-right when peeled and applied):
#     #
#     #  ┌──────────┬───────────────────┬──────────┬─────────┐
#     #  │          │  ↑ PRODUCT NAME ↑ │  ↑ CODE ↑│  ↑ MRP ↑│
#     #  │  [QR]    │   (rotated vert)  │ (rotated)│(rotated)│
#     #  │          │                   │          │         │
#     #  └──────────┴───────────────────┴──────────┴─────────┘
#     #
#     # All three text columns are rotated -90° so they read from bottom to top.
#     # "align='bottom'" means text is pushed toward the BOTTOM edge of the label
#     # (= the right side / label-cut edge when reading the rotated text upward).
#
#     def _build_html_small(self, label_list):
#         MM = 3.7795
#
#         # ── Label dimensions (mm) ─────────────────────────────────────────────
#         LW_MM       = 25.0   # total label width
#         LH_MM       = 15.0   # total label height
#         QR_MM       = 7.5    # QR image size
#         QR_COL_MM   = 10.0   # QR column width  (reduced to give more space to text)
#         CODE_COL_MM = 5.5    # label-code column width  ← NEW rotated column
#         NAME_COL_MM = 6.5    # product-name column width
#         MRP_COL_MM  = 3.0    # MRP column width
#
#         COL_GAP_MM = 7.0
#         L_MAR_MM   = 15.0
#         PW_MM      = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
#
#         LW = LW_MM * MM
#         LH = LH_MM * MM
#         QC = QR_COL_MM   * MM
#         PW = PW_MM * MM
#
#         def px(mm): return str(round(mm * MM, 2)) + 'px'
#
#         def _name_font(name):
#             n = len(name or '')
#             if n <= 8:    return '7pt'
#             elif n <= 14: return '6pt'
#             else:         return '5pt'
#
#         def _code_font(code):
#             n = len(code or '')
#             if n <= 8:    return '6pt'
#             elif n <= 12: return '5pt'
#             else:         return '4pt'
#
#         # ── Rotated-text cell helper ──────────────────────────────────────────
#         # Creates a <td> of width=col_w_mm, height=LH_MM.
#         # Inside it places a div that is LH wide × col_w tall, then rotates it
#         # -90°, so it becomes col_w wide × LH tall — exactly filling the cell.
#         #
#         # align='bottom'  → text sits at the BOTTOM edge of the label
#         #                   (visually the right/cut edge when reading rotated text)
#         # align='center'  → text centred in the column
#         def rotated_cell(text, col_w_mm, font_size, extra_style='', align='bottom'):
#             col_w = col_w_mm * MM
#             # After rotating the inner div by -90°, its top-left corner shifts.
#             # We compensate with negative margin so the div stays inside the td.
#             shift = (LH - col_w) / 2.0
#             transform = (
#                 'transform:rotate(-90deg);'
#                 '-webkit-transform:rotate(-90deg);'
#                 'transform-origin:50% 50%;'
#                 '-webkit-transform-origin:50% 50%;'
#             )
#             # justify-content acts on the PRE-rotation axis (vertical = LH tall).
#             # 'flex-end'   → content at bottom of LH  → after -90°: LEFT of label
#             # 'flex-start' → content at top of LH     → after -90°: RIGHT of label
#             # We want text toward the bottom edge of the label (right after rotate)
#             # so use 'flex-start'.
#             justify = 'flex-start' if align == 'bottom' else 'center'
#             rotated_div = (
#                 '<div style="'
#                 'width:' + str(round(LH, 2)) + 'px;'
#                 'height:' + str(round(col_w, 2)) + 'px;'
#                 'display:flex;'
#                 'flex-direction:column;'
#                 'align-items:center;'
#                 'justify-content:' + justify + ';'
#                 'overflow:hidden;'
#                 'font-size:' + font_size + ';'
#                 'font-weight:bold;'
#                 'padding:1px 3px;'
#                 'padding-left:5px;'
#                 + extra_style
#                 + transform
#                 + 'margin-top:' + str(round(-shift, 2)) + 'px;'
#                 'margin-left:' + str(round(-shift, 2)) + 'px;'
#                 '">' + text + '</div>'
#             )
#             return (
#                 '<td style="'
#                 'width:' + str(round(col_w, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'overflow:hidden;'
#                 'padding:0;'
#                 'vertical-align:middle;'
#                 'text-align:center;">'
#                 + rotated_div
#                 + '</td>'
#             )
#
#         def one_label(lbl):
#             name = lbl['name'] or ''
#             code = lbl.get('label_code') or ''
#
#             # ── Col 1: QR image only (no code below it anymore) ───────────────
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + px(QR_MM) + ';height:' + px(QR_MM) + ';'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#             col1 = (
#                 '<td style="width:' + str(round(QC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;text-align:center;'
#                 'padding:1px;overflow:hidden;">'
#                 + qr_html
#                 + '</td>'
#             )
#
#             div0 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
#
#             # ── Col 2: Product name — rotated, pushed to bottom ───────────────
#             def wrap_name(n, chars_per_line=7):
#                 words = n.split()
#                 lines = []
#                 current = ''
#                 for w in words:
#                     if current and len(current) + 1 + len(w) > chars_per_line:
#                         lines.append(current)
#                         current = w
#                     else:
#                         current = (current + ' ' + w).strip()
#                 if current:
#                     lines.append(current)
#                 return '<br/>'.join(lines)
#
#             wrapped_name = wrap_name(name.upper())
#             col2 = rotated_cell(
#                 wrapped_name,
#                 NAME_COL_MM,
#                 _name_font(name),
#                 extra_style=(
#                     'text-transform:uppercase;'
#                     'letter-spacing:0.2px;'
#                     'white-space:normal;'
#                     'word-break:break-word;'
#                     'text-align:center;'
#                     'line-height:1.2;'
#                 ),
#                 align='bottom',
#             )
#
#             div1 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
#
#             # ── Col 3: Label code — rotated, pushed to bottom ─────────────────
#             col3_empty = (
#                 '<td style="width:' + str(round(CODE_COL_MM * MM, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
#             )
#             if self.show_label_code and code:
#                 col3 = rotated_cell(
#                     code,
#                     CODE_COL_MM,
#                     _code_font(code),
#                     extra_style='white-space:nowrap;letter-spacing:0.3px;',
#                     align='bottom',
#                 )
#             else:
#                 col3 = col3_empty
#
#             div2 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
#
#             # ── Col 4: MRP — rotated, pushed to bottom ────────────────────────
#             col4_empty = (
#                 '<td style="width:' + str(round(MRP_COL_MM * MM, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
#             )
#             if self.show_mrp:
#                 mrp_text = 'MRP Rs.' + str(lbl['mrp'])
#                 col4 = rotated_cell(
#                     mrp_text,
#                     MRP_COL_MM,
#                     '5pt',
#                     extra_style='white-space:nowrap;',
#                     align='bottom',
#                 )
#             else:
#                 col4 = col4_empty
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(round(LW, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'border:1.5px solid #888;'
#                 'border-radius:' + px(2) + ';'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 '<tr>' + col1 + div0 + col2 + div1 + col3 + div2 + col4 + '</tr>'
#                 '</table>'
#             )
#
#         # ── Page layout: 2 labels per page ───────────────────────────────────
#         GAP = COL_GAP_MM * MM
#         MAR = L_MAR_MM   * MM
#         PH  = (LH_MM + 2) * MM
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
#                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="'
#                 'width:' + str(round(PW, 2)) + 'px;'
#                 'height:' + str(round(PH, 2)) + 'px;'
#                 'padding-top:' + str(round(1 * MM, 2)) + 'px;'
#                 'padding-left:' + str(round(MAR, 2)) + 'px;'
#                 'page-break-after:always;'
#                 'box-sizing:border-box;">'
#                 '<table style="'
#                 'width:' + str(round(2 * LW + GAP, 2)) + 'px;'
#                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
#                 + row + '</table></div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             'html, body {'
#             "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
#             '  background:white;'
#             '}'
#             '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW_MM, LH_MM + 2
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
        LW = 65
        QR_H = 26
        BOT_H = 28
        LH = QR_H + BOT_H
        QR_SIZE = 18
        COL_GAP = 60
        ROW_GAP = 4
        L_MAR = 13
        PW = 160

        def _name_font_size(name):
            n = len(name or '')
            if n <= 10:
                return 20
            elif n <= 15:
                return 16
            elif n <= 22:
                return 13
            else:
                return 10

        def _code_font_size(code):
            n = len(code or '')
            if n <= 6:
                return 18
            elif n <= 10:
                return 15
            else:
                return 12

        def one_label(lbl):
            qr_html = ''
            if self.show_qr:
                qr_html = (
                        '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                                                                             'style="width:' + str(
                    QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
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

            name = lbl['name'] or ''
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
            left = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                    '<tr>'
                    '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
                    + one_label(left) + '</td>'
                                        '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
                                                                             '<td style="width:' + str(
                LW) + 'mm;vertical-align:top;padding:0;">'
                    + (one_label(right) if right else '') + '</td>'
                                                            '</tr>'
            )

            pages_html.append(
                '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
                                                                              'padding-top:2mm;padding-left:' + str(
                    L_MAR) + 'mm;'
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

    # ── SMALL label HTML builder (25×15mm, 2 per row) ─────────────────────────

    def _build_html_small(self, label_list):
        MM = 3.7795

        # ── Label dimensions (mm) ─────────────────────────────────────────────
        # Layout: [QR] | [Name vertical] | [Code vertical] | [MRP vertical]
        # Uses writing-mode:vertical-rl + rotate(180deg).
        # Text reads bottom-to-top; vertical-align:bottom keeps it at
        # the bottom edge of the label. white-space:normal allows wrapping
        # so full text fits within the label height (= column width after rotation).
        LW_MM = 25.0
        LH_MM = 15.0
        QR_MM = 7.5
        QR_COL_MM = 9.0  # QR column - enough for the image
        NAME_COL_MM = 9.0  # product name column (wide - text wraps here)
        CODE_COL_MM = 5.0  # label code column
        MRP_COL_MM = 4.0  # MRP column (e.g. "MRP Rs.300")
        # Total: 9+9+5+4 = 27 but dividers add ~1mm each (3 dividers = ~0.8mm)
        # Actual label width = 25mm, we scale via MM constant

        COL_GAP_MM = 7.0
        L_MAR_MM = 26.0
        PW_MM = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM

        LW = LW_MM * MM
        LH = LH_MM * MM
        PW = PW_MM * MM

        # Recalculate column widths to exactly fill label width
        # Total text cols = NAME + CODE + MRP = 9+5+4 = 18mm
        # QR col = 9mm, 3 dividers ~0.3px each (negligible in mm)
        # 9 + 18 = 27mm > 25mm so scale down proportionally
        total_mm = QR_COL_MM + NAME_COL_MM + CODE_COL_MM + MRP_COL_MM  # 27
        scale = (LW_MM - 0.5) / total_mm  # fit into 24.5mm leaving 0.5 for borders
        QC = QR_COL_MM * scale * MM
        NC = NAME_COL_MM * scale * MM
        CC = CODE_COL_MM * scale * MM
        MC = MRP_COL_MM * scale * MM

        def px(mm):
            return str(round(mm * MM, 2)) + 'px'

        def _name_font(name):
            n = len(name or '')
            if n <= 8:
                return '8pt'
            elif n <= 14:
                return '7pt'
            else:
                return '6pt'

        def _code_font(code):
            n = len(code or '')
            if n <= 8:
                return '7pt'
            elif n <= 12:
                return '6pt'
            else:
                return '5pt'

        # ── Vertical text cell (writing-mode, wkhtmltopdf-safe) ───────────────
        # writing-mode:vertical-rl  → text flows top-to-bottom rotated right
        # rotate(180deg)            → flips to bottom-to-top (reads upward ↑)
        # vertical-align:bottom     → pushes text block to bottom of the <td>
        # text-align:right on td    → after rotation maps to bottom of label ✓
        # white-space:normal        → allows text to wrap across multiple "lines"
        #                             (in vertical mode, lines are horizontal stacks)
        # max-width on inner div    → limits how wide the text can grow = LH px
        def vertical_cell(text, col_px, font_size, extra_style=''):
            return (
                    '<td style="' +
                    'width:' + str(round(col_px, 2)) + 'px;' +
                    'height:' + str(round(LH, 2)) + 'px;' +
                    'vertical-align:bottom;' +
                    'text-align:center;' +
                    'padding:0 0 1px 0;' +
                    'overflow:hidden;">' +
                    '<div style="' +
                    'display:inline-block;' +
                    'writing-mode:vertical-rl;' +
                    '-webkit-writing-mode:vertical-rl;' +
                    'transform:rotate(180deg);' +
                    '-webkit-transform:rotate(180deg);' +
                    'font-size:' + font_size + ';' +
                    'font-weight:bold;' +
                    'white-space:normal;' +
                    'word-break:break-all;' +
                    'overflow:hidden;' +
                    'max-width:' + str(round(LH - 2, 2)) + 'px;' +
                    'text-align:left;' +
                    extra_style +
                    '">' + text + '</div>' +
                    '</td>'
            )

        def one_label(lbl):
            name = lbl['name'] or ''
            code = lbl.get('label_code') or ''

            # ── Col 1: QR image ───────────────────────────────────────────────
            qr_html = ''
            if self.show_qr:
                qr_html = (
                        '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                                                                             'style="width:' + str(
                    round(QC - 2, 2)) + 'px;' +
                        'height:' + str(round(QC - 2, 2)) + 'px;' +
                        'display:block;margin:0 auto;" alt=""/>'
                )
            col1 = (
                    '<td style="width:' + str(round(QC, 2)) + 'px;' +
                    'height:' + str(round(LH, 2)) + 'px;' +
                    'vertical-align:middle;text-align:center;' +
                    'padding:1px;overflow:hidden;">' +
                    qr_html + '</td>'
            )

            div0 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'

            # ── Col 2: Product name vertical ──────────────────────────────────
            col2 = vertical_cell(
                name.upper(),
                NC,
                _name_font(name),
                extra_style='letter-spacing:0.3px;',
            )

            div1 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'

            # ── Col 3: Label code vertical ────────────────────────────────────
            if self.show_label_code and code:
                col3 = vertical_cell(code, CC, _code_font(code))
            else:
                col3 = (
                        '<td style="width:' + str(round(CC, 2)) + 'px;' +
                        'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
                )

            div2 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'

            # ── Col 4: MRP vertical ───────────────────────────────────────────
            if self.show_mrp:
                col4 = vertical_cell(
                    'MRP Rs.' + str(lbl['mrp']),
                    MC,
                    '5pt',
                )
            else:
                col4 = (
                        '<td style="width:' + str(round(MC, 2)) + 'px;' +
                        'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
                )

            return (
                    '<table style="' +
                    'border-collapse:collapse;' +
                    'width:' + str(round(LW, 2)) + 'px;' +
                    'height:' + str(round(LH, 2)) + 'px;' +
                    'border:1.5px solid #888;' +
                    'border-radius:' + px(2) + ';' +
                    'background:white;' +
                    'table-layout:fixed;">' +
                    '<tr>' + col1 + div0 + col2 + div1 + col3 + div2 + col4 + '</tr>' +
                    '</table>'
            )

        # ── Page layout: 2 labels per page ───────────────────────────────────
        GAP = COL_GAP_MM * MM
        MAR = L_MAR_MM * MM
        PH = (LH_MM + 2) * MM

        pages_html = []
        i = 0
        while i < len(label_list):
            left = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                    '<tr>' +
                    '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">' +
                    one_label(left) + '</td>' +
                    '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>' +
                    '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">' +
                    (one_label(right) if right else '') + '</td>' +
                    '</tr>'
            )

            pages_html.append(
                '<div style="' +
                'width:' + str(round(PW, 2)) + 'px;' +
                'height:' + str(round(PH, 2)) + 'px;' +
                'padding-top:' + str(round(1 * MM, 2)) + 'px;' +
                'padding-left:' + str(round(MAR, 2)) + 'px;' +
                'page-break-after:always;' +
                'box-sizing:border-box;">' +
                '<table style="' +
                'width:' + str(round(2 * LW + GAP, 2)) + 'px;' +
                'border-collapse:separate;border-spacing:0;table-layout:fixed;">' +
                row + '</table></div>'
            )

        html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8"/>' +
                '<style>' +
                '* { margin:0; padding:0; box-sizing:border-box; }' +
                'html, body {' +
                "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;" +
                '  background:white;' +
                '}' +
                '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }' +
                '</style></head><body>' +
                ''.join(pages_html) +
                '</body></html>'
        )
        return html, PW_MM, LH_MM + 2

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
                '--page-width', str(page_w) + 'mm',
                '--page-height', str(page_h) + 'mm',
                '--margin-top', '0',
                '--margin-bottom', '0',
                '--margin-left', '0',
                '--margin-right', '0',
                '--disable-smart-shrinking',
                '--zoom', '1',
                '--dpi', '203',
                '--no-stop-slow-scripts',
                '--encoding', 'UTF-8',
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
                'pdf_url': pdf_url,
                'record_name': record_name,
                'label_qty': self.quantity,
                'product_count': len(products),
            },
        }