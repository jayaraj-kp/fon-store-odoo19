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
#         ('large', 'Large Label (65x54mm) — GP-1125T Roll'),
#         ('small', 'Small Label (25x15mm)'),
#         ('medium', 'Medium Label (40x25mm) — Barcode'),
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
#     # ── Barcode generator (Code128 -> base64 PNG) ─────────────────────────────
#
#     def _make_barcode_base64(self, value):
#         try:
#             import barcode as python_barcode
#             from barcode.writer import ImageWriter
#             code = python_barcode.get(
#                 'code128',
#                 str(value or 'LABEL'),
#                 writer=ImageWriter(),
#             )
#             buf = io.BytesIO()
#             code.write(buf, options={
#                 'module_height': 12.0,
#                 'module_width':  0.28,
#                 'quiet_zone':    1.5,
#                 'font_size':     0,
#                 'text_distance': 1.0,
#                 'write_text':    False,
#                 'background':    'white',
#                 'foreground':    'black',
#                 'dpi':           203,
#             })
#             return base64.b64encode(buf.getvalue()).decode('ascii')
#         except Exception:
#             return (
#                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
#                 'AAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
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
#             bc_value = product.barcode or product.default_code or label_code or str(product.id)
#             bc_b64 = self._make_barcode_base64(bc_value)
#             for _i in range(self.quantity):
#                 label_list.append({
#                     'name':       tmpl.name or '',
#                     'label_code': label_code,
#                     'mrp':        mrp,
#                     'qr_b64':     qr_b64,
#                     'bc_b64':     bc_b64,
#                     'bc_value':   bc_value,
#                 })
#         return label_list
#
#     # ── LARGE label HTML builder (65x54mm, GP-1125T roll) ────────────────────
#
#     def _build_html_large(self, label_list):
#         LW      = 65
#         QR_H    = 28.5
#         BOT_H   = 28
#         LH      = QR_H + BOT_H
#         QR_SIZE = 28.5
#         COL_GAP = 60
#         ROW_GAP = 4
#         L_MAR   = 9
#         PW      = 158
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
#                 'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;padding-top:2mm;'
#                 'vertical-align:top;overflow:hidden;">'
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
#     # ── SMALL label HTML builder (25x15mm, 2 per row) ────────────────────────
#
#     def _build_html_small(self, label_list):
#         MM = 3.7795  # mm -> px
#
#         LW_MM = 25.0
#         LH_MM = 15.0
#
#         QR_COL_MM  = 11.0
#         TXT_COL_MM = LW_MM - QR_COL_MM
#
#         QR_SIZE_MM = 11.0
#
#         COL_GAP_MM = 8.0
#         L_MAR_MM   = 32.0
#         PW_MM      = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
#
#         LW = LW_MM * MM
#         LH = LH_MM * MM
#         QC = QR_COL_MM * MM
#         TC = TXT_COL_MM * MM
#         PW = PW_MM * MM
#
#         def px(mm):
#             return str(round(mm * MM, 2)) + 'px'
#
#         def _name_font(name):
#             n = len(name or '')
#             if n <= 8:    return '6.5pt'
#             elif n <= 14: return '6pt'
#             elif n <= 20: return '5pt'
#             else:         return '4pt'
#
#         def _code_font(code):
#             n = len(code or '')
#             if n <= 8:    return '6pt'
#             elif n <= 12: return '5pt'
#             else:         return '4pt'
#
#         def one_label(lbl):
#             name = lbl['name'] or ''
#             code = lbl.get('label_code') or ''
#             mrp  = lbl.get('mrp', 0)
#
#             qr_html = ''
#             if self.show_qr:
#                 qr_html = (
#                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
#                     'style="width:' + px(QR_SIZE_MM) + ';height:' + px(QR_SIZE_MM) + ';'
#                     'display:block;margin:0 auto;" alt=""/>'
#                 )
#             col_qr = (
#                 '<td style="'
#                 'width:' + str(round(QC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;text-align:center;'
#                 'padding:1px;overflow:hidden;">'
#                 + qr_html + '</td>'
#             )
#
#             divider = '<td style="width:1px;padding:0;border-left:1.5px dashed #aaa;"></td>'
#
#             max_w = str(round(LH - 6, 2)) + 'px'
#             shift = (LH - TC) / 2.0
#
#             name_line = ''
#             if name:
#                 name_line = (
#                     '<div style="font-size:' + _name_font(name) + ';'
#                     'text-transform:uppercase;white-space:normal;word-break:break-word;'
#                     'overflow:hidden;max-width:' + max_w + ';line-height:1.25;margin-top:2px;">'
#                     + name.upper() + '</div>'
#                 )
#
#             code_line = ''
#             if self.show_label_code and code:
#                 code_line = (
#                     '<div style="font-size:' + _code_font(code) + ';'
#                     'white-space:normal;word-break:break-all;overflow:hidden;'
#                     'max-width:' + max_w + ';margin-top:2px;line-height:1.2;">'
#                     + code + '</div>'
#                 )
#
#             mrp_line = ''
#             if self.show_mrp:
#                 mrp_line = (
#                     '<div style="font-size:7pt;white-space:normal;word-break:break-word;'
#                     'overflow:hidden;max-width:' + max_w + ';margin-top:2px;line-height:1.2;">'
#                     'MRP Rs.' + str(mrp) + '</div>'
#                 )
#
#             rotated_div = (
#                 '<div style="width:' + str(round(LH, 2)) + 'px;'
#                 'height:' + str(round(TC, 2)) + 'px;'
#                 'display:flex;flex-direction:column;align-items:flex-start;'
#                 'justify-content:center;overflow:hidden;'
#                 'transform:rotate(-90deg);-webkit-transform:rotate(-90deg);'
#                 'transform-origin:50% 50%;-webkit-transform-origin:50% 50%;'
#                 'margin-top:' + str(round(-shift, 2)) + 'px;'
#                 'margin-left:' + str(round(-shift, 2)) + 'px;padding:0 3px;">'
#                 + name_line + code_line + mrp_line + '</div>'
#             )
#
#             col_txt = (
#                 '<td style="width:' + str(round(TC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;text-align:center;padding:0;overflow:hidden;">'
#                 + rotated_div + '</td>'
#             )
#
#             return (
#                 '<table style="border-collapse:collapse;'
#                 'width:' + str(round(LW, 2)) + 'px;height:' + str(round(LH, 2)) + 'px;'
#                 'border:1.5px solid #888;border-radius:' + px(1.5) + ';'
#                 'background:white;table-layout:fixed;">'
#                 '<tr>' + col_qr + divider + col_txt + '</tr></table>'
#             )
#
#         GAP = COL_GAP_MM * MM
#         MAR = L_MAR_MM * MM
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
#                 '<div style="width:' + str(round(PW, 2)) + 'px;'
#                 'height:' + str(round(PH, 2)) + 'px;'
#                 'padding-top:' + str(round(1 * MM, 2)) + 'px;'
#                 'padding-left:' + str(round(MAR, 2)) + 'px;'
#                 'page-break-after:always;box-sizing:border-box;">'
#                 '<table style="width:' + str(round(2 * LW + GAP, 2)) + 'px;'
#                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
#                 + row + '</table></div>'
#             )
#
#         html = (
#             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#             '<style>'
#             '* { margin:0; padding:0; box-sizing:border-box; }'
#             "html, body { font-family: 'Arial Narrow', Arial, Helvetica, sans-serif; background:white; }"
#             '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW_MM, LH_MM + 2
#
#     # ── MEDIUM label HTML builder (40x25mm, 2 per row) ───────────────────────
#     #
#     # Layout matches your physical label:
#     #
#     #  ┌────────────────────────────────────────┐
#     #  │         KEYCHAIN MINI BIKE             │  ← bold uppercase, centred
#     #  │- - - - - - - - - - - - - - - - - - - -│  ← dashed separator
#     #  │  ||||||||||||||||||||||||||||||||||||  │  ← barcode, full width
#     #  │  KC11034                MRP Rs.9999   │  ← code left, MRP right
#     #  └────────────────────────────────────────┘
#     #
#     # KEY FIXES vs previous version:
#     #   • Page width = exactly 2×LW + small gap + tiny margin → Scale = 100%
#     #   • Left margin is minimal (1mm) so labels start at the left edge
#     #   • Barcode is wider (uses max-width:38mm) and taller (12mm)
#     #   • Fonts are larger throughout
#
#     def _build_html_medium(self, label_list):
#         # ── Dimensions ────────────────────────────────────────────────────────
#         LW_MM      = 40.0          # label width
#         LH_MM      = 25.0          # label height
#         COL_GAP_MM = 9.0           # gap between the two labels
#         L_MAR_MM   = 10.0           # left margin on the page
#         # Total page width = left_margin + label + gap + label + left_margin
#         PW_MM      = L_MAR_MM + LW_MM + COL_GAP_MM + LW_MM + L_MAR_MM   # 84 mm
#         PH_MM      = LH_MM + 2     # 27 mm  (tiny top/bottom breathing room)
#
#         def _name_font(name):
#             n = len(name or '')
#             if n <= 12:   return '11pt'
#             elif n <= 20: return '9pt'
#             elif n <= 28: return '7.5pt'
#             else:         return '6pt'
#
#         def _code_font(code):
#             n = len(code or '')
#             if n <= 10:   return '9pt'
#             elif n <= 16: return '8pt'
#             else:         return '7pt'
#
#         def one_label(lbl):
#             name   = lbl['name'] or ''
#             code   = lbl.get('label_code') or ''
#             mrp    = lbl.get('mrp', 0)
#             bc_b64 = lbl.get('bc_b64', '')
#
#             # ── Row 1: Product name ───────────────────────────────────────────
#             name_row = (
#                 '<tr><td style="'
#                 'padding:2mm 2mm 1mm 2mm;'
#                 'text-align:center;'
#                 'font-size:' + _name_font(name) + ';'
#                 'font-weight:bold;'
#                 'text-transform:uppercase;'
#                 'letter-spacing:0.5px;'
#                 'white-space:normal;'
#                 'word-break:break-word;'
#                 'line-height:1.2;'
#                 'overflow:hidden;'
#                 'border-bottom:1.5px dashed #aaa;">'
#                 + name.upper()
#                 + '</td></tr>'
#             )
#
#             # ── Row 2: Barcode ────────────────────────────────────────────────
#             barcode_img = ''
#             if bc_b64:
#                 barcode_img = (
#                     '<img src="data:image/png;base64,' + bc_b64 + '" '
#                     'style="'
#                     'height:16mm;'
#                     'max-width:39mm;'
#                     'display:block;'
#                     'margin:0 auto;" alt=""/>'
#                 )
#             barcode_row = (
#                 '<tr><td style="'
#                 'padding:1mm 1mm 1mm 1mm;'
#                 'text-align:center;'
#                 'vertical-align:middle;">'
#                 + barcode_img
#                 + '</td></tr>'
#             )
#
#             # ── Row 3: Code left, MRP right ───────────────────────────────────
#             code_cell = ''
#             if self.show_label_code and code:
#                 code_cell = (
#                     '<td style="'
#                     'width:50%;'
#                     'text-align:left;vertical-align:middle;'
#                     'font-size:' + _code_font(code) + ';'
#                     'font-weight:bold;'
#                     'white-space:nowrap;">'
#                     + code + '</td>'
#                 )
#             else:
#                 code_cell = '<td></td>'
#
#             mrp_cell = ''
#             if self.show_mrp:
#                 mrp_cell = (
#                     '<td style="'
#                     'width:50%;'
#                     'text-align:right;vertical-align:middle;'
#                     'font-size:9pt;'
#                     'font-weight:bold;'
#                     'white-space:nowrap;">'
#                     'MRP Rs.' + str(mrp) + '</td>'
#                 )
#             else:
#                 mrp_cell = '<td></td>'
#
#             bottom_row = (
#                 '<tr><td style="padding:0.5mm 2mm 1.5mm 2mm;">'
#                 '<table style="width:100%;border-collapse:collapse;table-layout:fixed;">'
#                 '<tr>' + code_cell + mrp_cell + '</tr>'
#                 '</table>'
#                 '</td></tr>'
#             )
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(LW_MM) + 'mm;'
#                 'height:' + str(LH_MM) + 'mm;'
#                 'border:1.5px solid #888;'
#                 'border-radius:1.5mm;'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 + name_row
#                 + barcode_row
#                 + bottom_row
#                 + '</table>'
#             )
#
#         # ── Page layout: 2 labels per page, no scaling needed ─────────────────
#         pages_html = []
#         i = 0
#         while i < len(label_list):
#             left  = label_list[i]
#             right = label_list[i + 1] if (i + 1) < len(label_list) else None
#             i += 2
#
#             row = (
#                 '<tr>'
#                 '<td style="width:' + str(LW_MM) + 'mm;vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(COL_GAP_MM) + 'mm;padding:0;border:none;"></td>'
#                 '<td style="width:' + str(LW_MM) + 'mm;vertical-align:top;padding:0;">'
#                 + (one_label(right) if right else '') + '</td>'
#                 '</tr>'
#             )
#
#             pages_html.append(
#                 '<div style="'
#                 'width:' + str(PW_MM) + 'mm;'
#                 'height:' + str(PH_MM) + 'mm;'
#                 'padding-top:1mm;'
#                 'padding-left:' + str(L_MAR_MM) + 'mm;'
#                 'page-break-after:always;'
#                 'box-sizing:border-box;">'
#                 '<table style="'
#                 'width:' + str(LW_MM + COL_GAP_MM + LW_MM) + 'mm;'
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
#             '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(PH_MM) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW_MM, PH_MM
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
#         elif self.label_type == 'medium':
#             html_content, page_w, page_h = self._build_html_medium(label_list)
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
        ('large', 'Large Label (65x54mm) — GP-1125T Roll'),
        ('small', 'Small Label (25x15mm)'),
        ('medium', 'Medium Label (40x25mm) — Barcode'),
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

    # ── Barcode generator (Code128 -> base64 PNG) ─────────────────────────────
    # FIXED: module_width increased to 0.5 (was 0.28) so bars are wide enough
    # for a 203 DPI thermal printer to print cleanly and scanners to read them.
    # quiet_zone increased to 6.5 (required by Code128 spec).

    def _make_barcode_base64(self, value):
        try:
            import barcode as python_barcode
            from barcode.writer import ImageWriter
            code = python_barcode.get(
                'code128',
                str(value or 'LABEL'),
                writer=ImageWriter(),
            )
            buf = io.BytesIO()
            code.write(buf, options={
                'module_height': 15.0,   # taller bars → easier to scan
                'module_width':  0.5,    # FIXED: ~4 dots per bar at 203 DPI ✓
                'quiet_zone':    6.5,    # required quiet zone for Code128 spec
                'font_size':     0,
                'text_distance': 1.0,
                'write_text':    False,
                'background':    'white',
                'foreground':    'black',
                'dpi':           203,
            })
            return base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception:
            return (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
                'AAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
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
            bc_value = product.barcode or product.default_code or label_code or str(product.id)
            bc_b64 = self._make_barcode_base64(bc_value)
            for _i in range(self.quantity):
                label_list.append({
                    'name':       tmpl.name or '',
                    'label_code': label_code,
                    'mrp':        mrp,
                    'qr_b64':     qr_b64,
                    'bc_b64':     bc_b64,
                    'bc_value':   bc_value,
                })
        return label_list

    # ── LARGE label HTML builder (65x54mm, GP-1125T roll) ────────────────────
    # !! UNCHANGED !!

    def _build_html_large(self, label_list):
        LW      = 65
        QR_H    = 28.5
        BOT_H   = 28
        LH      = QR_H + BOT_H
        QR_SIZE = 28.5
        COL_GAP = 60
        ROW_GAP = 4
        L_MAR   = 9
        PW      = 158

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
                'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;padding-top:2mm;'
                'vertical-align:top;overflow:hidden;">'
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

    # ── SMALL label HTML builder (25x15mm, 2 per row) ────────────────────────
    # !! UNCHANGED !!

    def _build_html_small(self, label_list):
        MM = 3.7795  # mm -> px

        LW_MM = 25.0
        LH_MM = 15.0

        QR_COL_MM  = 11.0
        TXT_COL_MM = LW_MM - QR_COL_MM

        QR_SIZE_MM = 11.0

        COL_GAP_MM = 8.0
        L_MAR_MM   = 32.0
        PW_MM      = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM

        LW = LW_MM * MM
        LH = LH_MM * MM
        QC = QR_COL_MM * MM
        TC = TXT_COL_MM * MM
        PW = PW_MM * MM

        def px(mm):
            return str(round(mm * MM, 2)) + 'px'

        def _name_font(name):
            n = len(name or '')
            if n <= 8:    return '6.5pt'
            elif n <= 14: return '6pt'
            elif n <= 20: return '5pt'
            else:         return '4pt'

        def _code_font(code):
            n = len(code or '')
            if n <= 8:    return '6pt'
            elif n <= 12: return '5pt'
            else:         return '4pt'

        def one_label(lbl):
            name = lbl['name'] or ''
            code = lbl.get('label_code') or ''
            mrp  = lbl.get('mrp', 0)

            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + px(QR_SIZE_MM) + ';height:' + px(QR_SIZE_MM) + ';'
                    'display:block;margin:0 auto;" alt=""/>'
                )
            col_qr = (
                '<td style="'
                'width:' + str(round(QC, 2)) + 'px;'
                'height:' + str(round(LH, 2)) + 'px;'
                'vertical-align:middle;text-align:center;'
                'padding:1px;overflow:hidden;">'
                + qr_html + '</td>'
            )

            divider = '<td style="width:1px;padding:0;border-left:1.5px dashed #aaa;"></td>'

            max_w = str(round(LH - 6, 2)) + 'px'
            shift = (LH - TC) / 2.0

            name_line = ''
            if name:
                name_line = (
                    '<div style="font-size:' + _name_font(name) + ';'
                    'text-transform:uppercase;white-space:normal;word-break:break-word;'
                    'overflow:hidden;max-width:' + max_w + ';line-height:1.25;margin-top:2px;">'
                    + name.upper() + '</div>'
                )

            code_line = ''
            if self.show_label_code and code:
                code_line = (
                    '<div style="font-size:' + _code_font(code) + ';'
                    'white-space:normal;word-break:break-all;overflow:hidden;'
                    'max-width:' + max_w + ';margin-top:2px;line-height:1.2;">'
                    + code + '</div>'
                )

            mrp_line = ''
            if self.show_mrp:
                mrp_line = (
                    '<div style="font-size:7pt;white-space:normal;word-break:break-word;'
                    'overflow:hidden;max-width:' + max_w + ';margin-top:2px;line-height:1.2;">'
                    'MRP Rs.' + str(mrp) + '</div>'
                )

            rotated_div = (
                '<div style="width:' + str(round(LH, 2)) + 'px;'
                'height:' + str(round(TC, 2)) + 'px;'
                'display:flex;flex-direction:column;align-items:flex-start;'
                'justify-content:center;overflow:hidden;'
                'transform:rotate(-90deg);-webkit-transform:rotate(-90deg);'
                'transform-origin:50% 50%;-webkit-transform-origin:50% 50%;'
                'margin-top:' + str(round(-shift, 2)) + 'px;'
                'margin-left:' + str(round(-shift, 2)) + 'px;padding:0 3px;">'
                + name_line + code_line + mrp_line + '</div>'
            )

            col_txt = (
                '<td style="width:' + str(round(TC, 2)) + 'px;'
                'height:' + str(round(LH, 2)) + 'px;'
                'vertical-align:middle;text-align:center;padding:0;overflow:hidden;">'
                + rotated_div + '</td>'
            )

            return (
                '<table style="border-collapse:collapse;'
                'width:' + str(round(LW, 2)) + 'px;height:' + str(round(LH, 2)) + 'px;'
                'border:1.5px solid #888;border-radius:' + px(1.5) + ';'
                'background:white;table-layout:fixed;">'
                '<tr>' + col_qr + divider + col_txt + '</tr></table>'
            )

        GAP = COL_GAP_MM * MM
        MAR = L_MAR_MM * MM
        PH  = (LH_MM + 2) * MM

        pages_html = []
        i = 0
        while i < len(label_list):
            left  = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                '<tr>'
                '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
                + one_label(left) + '</td>'
                '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>'
                '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
                + (one_label(right) if right else '') + '</td>'
                '</tr>'
            )

            pages_html.append(
                '<div style="width:' + str(round(PW, 2)) + 'px;'
                'height:' + str(round(PH, 2)) + 'px;'
                'padding-top:' + str(round(1 * MM, 2)) + 'px;'
                'padding-left:' + str(round(MAR, 2)) + 'px;'
                'page-break-after:always;box-sizing:border-box;">'
                '<table style="width:' + str(round(2 * LW + GAP, 2)) + 'px;'
                'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
                + row + '</table></div>'
            )

        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<style>'
            '* { margin:0; padding:0; box-sizing:border-box; }'
            "html, body { font-family: 'Arial Narrow', Arial, Helvetica, sans-serif; background:white; }"
            '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }'
            '</style></head><body>'
            + ''.join(pages_html)
            + '</body></html>'
        )
        return html, PW_MM, LH_MM + 2

    # ── MEDIUM label HTML builder (40x25mm, 2 per row) ───────────────────────
    #
    # Layout:
    #  ┌────────────────────────────────────────┐
    #  │         PRODUCT NAME (centred)         │
    #  │- - - - - - - - - - - - - - - - - - - -│
    #  │  ||||||||||||||||||||||||||||||||||||  │  ← barcode, natural size, no rescale
    #  │  KC11034                MRP Rs.9999   │
    #  └────────────────────────────────────────┘
    #
    # KEY FIXES for barcode scanning:
    #   1. _make_barcode_base64: module_width=0.5 (was 0.28) → wider bars
    #   2. _make_barcode_base64: quiet_zone=6.5 (was 1.5) → proper quiet zone
    #   3. _make_barcode_base64: module_height=15.0 (was 12.0) → taller bars
    #   4. HTML img: width/height:auto → NO rescaling of barcode image
    #   5. HTML img: image-rendering:pixelated → no anti-alias blur on bars
    #   6. wkhtmltopdf --zoom 1 already set → no additional scaling

    def _build_html_medium(self, label_list):
        LW_MM      = 40.0
        LH_MM      = 25.0
        COL_GAP_MM = 9.0
        L_MAR_MM   = 10.0
        PW_MM      = L_MAR_MM + LW_MM + COL_GAP_MM + LW_MM + L_MAR_MM   # 109 mm
        PH_MM      = LH_MM + 2                                            # 27 mm

        def _name_font(name):
            n = len(name or '')
            if n <= 12:   return '11pt'
            elif n <= 20: return '9pt'
            elif n <= 28: return '7.5pt'
            else:         return '6pt'

        def _code_font(code):
            n = len(code or '')
            if n <= 10:   return '9pt'
            elif n <= 16: return '8pt'
            else:         return '7pt'

        def one_label(lbl):
            name   = lbl['name'] or ''
            code   = lbl.get('label_code') or ''
            mrp    = lbl.get('mrp', 0)
            bc_b64 = lbl.get('bc_b64', '')

            # ── Row 1: Product name ───────────────────────────────────────────
            name_row = (
                '<tr><td style="'
                'padding:2mm 2mm 1mm 2mm;'
                'text-align:center;'
                'font-size:' + _name_font(name) + ';'
                'font-weight:bold;'
                'text-transform:uppercase;'
                'letter-spacing:0.5px;'
                'white-space:normal;'
                'word-break:break-word;'
                'line-height:1.2;'
                'overflow:hidden;'
                'border-bottom:1.5px dashed #aaa;">'
                + name.upper()
                + '</td></tr>'
            )

            # ── Row 2: Barcode ─────────────────────────────────────────────────
            # FIXED: width/height auto so the PNG renders at its natural pixel
            # size → bar widths are preserved exactly as generated.
            # image-rendering:pixelated prevents wkhtmltopdf from blurring bars.
            barcode_img = ''
            if bc_b64:
                barcode_img = (
                    '<img src="data:image/png;base64,' + bc_b64 + '" '
                    'style="'
                    'width:auto;'
                    'height:auto;'
                    'max-width:38mm;'
                    'display:block;'
                    'margin:0 auto;'
                    'image-rendering:pixelated;'
                    '-ms-interpolation-mode:nearest-neighbor;" alt=""/>'
                )
            barcode_row = (
                '<tr><td style="'
                'padding:1mm 1mm 0.5mm 1mm;'
                'text-align:center;'
                'vertical-align:middle;">'
                + barcode_img
                + '</td></tr>'
            )

            # ── Row 3: Code left, MRP right ───────────────────────────────────
            code_cell = ''
            if self.show_label_code and code:
                code_cell = (
                    '<td style="'
                    'width:50%;'
                    'text-align:left;vertical-align:middle;'
                    'font-size:' + _code_font(code) + ';'
                    'font-weight:bold;'
                    'white-space:nowrap;">'
                    + code + '</td>'
                )
            else:
                code_cell = '<td></td>'

            mrp_cell = ''
            if self.show_mrp:
                mrp_cell = (
                    '<td style="'
                    'width:50%;'
                    'text-align:right;vertical-align:middle;'
                    'font-size:9pt;'
                    'font-weight:bold;'
                    'white-space:nowrap;">'
                    'MRP Rs.' + str(mrp) + '</td>'
                )
            else:
                mrp_cell = '<td></td>'

            bottom_row = (
                '<tr><td style="padding:0.5mm 2mm 1.5mm 2mm;">'
                '<table style="width:100%;border-collapse:collapse;table-layout:fixed;">'
                '<tr>' + code_cell + mrp_cell + '</tr>'
                '</table>'
                '</td></tr>'
            )

            return (
                '<table style="'
                'border-collapse:collapse;'
                'width:' + str(LW_MM) + 'mm;'
                'height:' + str(LH_MM) + 'mm;'
                'border:1.5px solid #888;'
                'border-radius:1.5mm;'
                'background:white;'
                'table-layout:fixed;">'
                + name_row
                + barcode_row
                + bottom_row
                + '</table>'
            )

        # ── Page layout: 2 labels per page ────────────────────────────────────
        pages_html = []
        i = 0
        while i < len(label_list):
            left  = label_list[i]
            right = label_list[i + 1] if (i + 1) < len(label_list) else None
            i += 2

            row = (
                '<tr>'
                '<td style="width:' + str(LW_MM) + 'mm;vertical-align:top;padding:0;">'
                + one_label(left) + '</td>'
                '<td style="width:' + str(COL_GAP_MM) + 'mm;padding:0;border:none;"></td>'
                '<td style="width:' + str(LW_MM) + 'mm;vertical-align:top;padding:0;">'
                + (one_label(right) if right else '') + '</td>'
                '</tr>'
            )

            pages_html.append(
                '<div style="'
                'width:' + str(PW_MM) + 'mm;'
                'height:' + str(PH_MM) + 'mm;'
                'padding-top:1mm;'
                'padding-left:' + str(L_MAR_MM) + 'mm;'
                'page-break-after:always;'
                'box-sizing:border-box;">'
                '<table style="'
                'width:' + str(LW_MM + COL_GAP_MM + LW_MM) + 'mm;'
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
            '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(PH_MM) + 'mm; }'
            '</style></head><body>'
            + ''.join(pages_html)
            + '</body></html>'
        )
        return html, PW_MM, PH_MM

    # ── Print action ──────────────────────────────────────────────────────────

    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        label_list = self._get_label_list()

        if self.label_type == 'small':
            html_content, page_w, page_h = self._build_html_small(label_list)
        elif self.label_type == 'medium':
            html_content, page_w, page_h = self._build_html_medium(label_list)
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