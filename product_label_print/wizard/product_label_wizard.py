# # #
# # # from odoo import models, fields, api, _
# # # from odoo.exceptions import UserError
# # # import base64
# # # import io
# # # import os
# # # import subprocess
# # # import tempfile
# # #
# # #
# # # class ProductLabelWizard(models.TransientModel):
# # #     _name = 'product.label.wizard'
# # #     _description = 'Product Label Printing Wizard'
# # #
# # #     product_tmpl_ids = fields.Many2many('product.template', string='Product Templates')
# # #     product_ids = fields.Many2many('product.product', string='Product Variants')
# # #     quantity = fields.Integer(string='Number of Labels per Product', default=1, required=True)
# # #     show_mrp = fields.Boolean(string='Show MRP', default=True)
# # #     show_qr = fields.Boolean(string='Show QR Code', default=True)
# # #     show_label_code = fields.Boolean(string='Show Label Code', default=True)
# # #     label_type = fields.Selection([
# # #         ('large', 'Large Label (65×54mm) — GP-1125T Roll'),
# # #         ('small', 'Small Label (25×15mm)'),
# # #     ], string='Label Size', default='large', required=True)
# # #
# # #     # ── QR generator ──────────────────────────────────────────────────────────
# # #
# # #     def _make_qr_base64(self, value):
# # #         try:
# # #             import qrcode
# # #             qr = qrcode.QRCode(
# # #                 version=1,
# # #                 error_correction=qrcode.constants.ERROR_CORRECT_L,
# # #                 box_size=8,
# # #                 border=1,
# # #             )
# # #             qr.add_data(value or 'LABEL')
# # #             qr.make(fit=True)
# # #             img = qr.make_image(fill_color='black', back_color='white')
# # #             buf = io.BytesIO()
# # #             img.save(buf, format='PNG')
# # #             return base64.b64encode(buf.getvalue()).decode('ascii')
# # #         except Exception:
# # #             return (
# # #                 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk'
# # #                 'YAAAAAYAAjCB0C8AAAAASUVORK5CYII='
# # #             )
# # #
# # #     # ── Product / label helpers ───────────────────────────────────────────────
# # #
# # #     def _get_products(self):
# # #         products = self.env['product.product']
# # #         if self.product_ids:
# # #             products |= self.product_ids
# # #         if self.product_tmpl_ids:
# # #             for tmpl in self.product_tmpl_ids:
# # #                 products |= tmpl.product_variant_ids
# # #         return products
# # #
# # #     def _get_label_list(self):
# # #         products = self._get_products()
# # #         label_list = []
# # #         for product in products:
# # #             tmpl = product.product_tmpl_id
# # #             label_code = (getattr(tmpl, 'label_code', None) or
# # #                           product.default_code or '')
# # #             mrp = int(tmpl.list_price or 0)
# # #             qr_value = (product.barcode or product.default_code or
# # #                         tmpl.name or str(product.id))
# # #             qr_b64 = self._make_qr_base64(qr_value)
# # #             for _i in range(self.quantity):
# # #                 label_list.append({
# # #                     'name': tmpl.name or '',
# # #                     'label_code': label_code,
# # #                     'mrp': mrp,
# # #                     'qr_b64': qr_b64,
# # #                 })
# # #         return label_list
# # #
# # #     # ── LARGE label HTML builder (65×54mm, GP-1125T roll) ────────────────────
# # #
# # #     def _build_html_large(self, label_list):
# # #         LW      = 65
# # #         QR_H    = 26
# # #         BOT_H   = 28
# # #         LH      = QR_H + BOT_H
# # #         QR_SIZE = 18
# # #         COL_GAP = 60
# # #         ROW_GAP = 4
# # #         L_MAR   = 13
# # #         PW      = 160
# # #
# # #         def _name_font_size(name):
# # #             n = len(name or '')
# # #             if n <= 10:   return 20
# # #             elif n <= 15: return 16
# # #             elif n <= 22: return 13
# # #             else:         return 10
# # #
# # #         def _code_font_size(code):
# # #             n = len(code or '')
# # #             if n <= 6:    return 18
# # #             elif n <= 10: return 15
# # #             else:         return 12
# # #
# # #         def one_label(lbl):
# # #             qr_html = ''
# # #             if self.show_qr:
# # #                 qr_html = (
# # #                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
# # #                     'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
# # #                     'display:block;margin:0 auto;" alt=""/>'
# # #                 )
# # #
# # #             code_html = ''
# # #             if self.show_label_code and lbl.get('label_code'):
# # #                 code_fs = str(_code_font_size(lbl['label_code'])) + 'pt'
# # #                 code_html = (
# # #                     '<div style="text-align:center;font-size:' + code_fs + ';'
# # #                     'font-weight:bold;letter-spacing:0.3mm;margin-top:1mm;'
# # #                     'word-break:break-all;overflow:hidden;">'
# # #                     + lbl['label_code'] + '</div>'
# # #                 )
# # #
# # #             top_cell = (
# # #                 '<tr><td style="height:' + str(QR_H) + 'mm;'
# # #                 'padding:3mm 1mm 1mm 5mm;vertical-align:top;'
# # #                 'border-bottom:1.5px dashed #aaa;">'
# # #                 + qr_html + code_html + '</td></tr>'
# # #             )
# # #
# # #             name    = lbl['name'] or ''
# # #             name_fs = str(_name_font_size(name)) + 'pt'
# # #             mrp_html = ''
# # #             if self.show_mrp:
# # #                 mrp_html = (
# # #                     '<div style="font-size:14pt;padding-left:4mm;margin-top:1mm;">'
# # #                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
# # #                 )
# # #
# # #             bot_cell = (
# # #                 '<tr><td style="height:' + str(BOT_H) + 'mm;'
# # #                 'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;'
# # #                 'vertical-align:bottom;overflow:hidden;">'
# # #                 '<div style="font-size:' + name_fs + ';'
# # #                 'text-transform:uppercase;word-break:break-word;'
# # #                 'word-wrap:break-word;white-space:normal;line-height:2;'
# # #                 'overflow:hidden;">'
# # #                 + name + '</div>' + mrp_html + '</td></tr>'
# # #             )
# # #
# # #             return (
# # #                 '<table style="border-collapse:collapse;width:' + str(LW) + 'mm;'
# # #                 'border:1.5px solid #888;border-radius:3mm;background:white;'
# # #                 'table-layout:fixed;">'
# # #                 + top_cell + bot_cell + '</table>'
# # #             )
# # #
# # #         page_h = 2 + LH + ROW_GAP + 2
# # #         pages_html = []
# # #         i = 0
# # #         while i < len(label_list):
# # #             left  = label_list[i]
# # #             right = label_list[i + 1] if (i + 1) < len(label_list) else None
# # #             i += 2
# # #
# # #             row = (
# # #                 '<tr>'
# # #                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
# # #                 + one_label(left) + '</td>'
# # #                 '<td style="width:' + str(COL_GAP) + 'mm;padding:0;border:none;"></td>'
# # #                 '<td style="width:' + str(LW) + 'mm;vertical-align:top;padding:0;">'
# # #                 + (one_label(right) if right else '') + '</td>'
# # #                 '</tr>'
# # #             )
# # #
# # #             pages_html.append(
# # #                 '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
# # #                 'padding-top:2mm;padding-left:' + str(L_MAR) + 'mm;'
# # #                 'page-break-after:always;box-sizing:border-box;">'
# # #                 '<table style="width:' + str(2 * LW + COL_GAP) + 'mm;'
# # #                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
# # #                 + row + '</table></div>'
# # #             )
# # #
# # #         html = (
# # #             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
# # #             '<style>'
# # #             '* { margin:0; padding:0; box-sizing:border-box; }'
# # #             'html, body {'
# # #             "  font-family: 'Arial Narrow', 'Liberation Sans', Arial, sans-serif;"
# # #             '  background: white;'
# # #             '  width: ' + str(PW) + 'mm;'
# # #             '}'
# # #             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
# # #             '</style></head><body>'
# # #             + ''.join(pages_html)
# # #             + '</body></html>'
# # #         )
# # #         return html, PW, page_h
# # #
# # #     # ── SMALL label HTML builder (25×15mm, 2 per row) ─────────────────────────
# # #     #
# # #     # Layout (label reads left-to-right when peeled and applied):
# # #     #
# # #     #  ┌──────────┬───────────────────┬──────────┬─────────┐
# # #     #  │          │  ↑ PRODUCT NAME ↑ │  ↑ CODE ↑│  ↑ MRP ↑│
# # #     #  │  [QR]    │   (rotated vert)  │ (rotated)│(rotated)│
# # #     #  │          │                   │          │         │
# # #     #  └──────────┴───────────────────┴──────────┴─────────┘
# # #     #
# # #     # All three text columns are rotated -90° so they read from bottom to top.
# # #     # "align='bottom'" means text is pushed toward the BOTTOM edge of the label
# # #     # (= the right side / label-cut edge when reading the rotated text upward).
# # #
# # #     def _build_html_small(self, label_list):
# # #         MM = 3.7795
# # #
# # #         # ── Label dimensions (mm) ─────────────────────────────────────────────
# # #         LW_MM       = 25.0   # total label width
# # #         LH_MM       = 15.0   # total label height
# # #         QR_MM       = 5.5    # QR image size
# # #         QR_COL_MM   = 8.0   # QR column width  (reduced to give more space to text)
# # #         CODE_COL_MM = 4.5    # label-code column width  ← NEW rotated column
# # #         NAME_COL_MM = 5.5    # product-name column width
# # #         MRP_COL_MM  = 2.0    # MRP column width
# # #
# # #         COL_GAP_MM = 4.0
# # #         L_MAR_MM   = 15.0
# # #         PW_MM      = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
# # #
# # #         LW = LW_MM * MM
# # #         LH = LH_MM * MM
# # #         QC = QR_COL_MM   * MM
# # #         PW = PW_MM * MM
# # #
# # #         def px(mm): return str(round(mm * MM, 2)) + 'px'
# # #
# # #         def _name_font(name):
# # #             n = len(name or '')
# # #             if n <= 8:    return '7pt'
# # #             elif n <= 14: return '6pt'
# # #             else:         return '5pt'
# # #
# # #         def _code_font(code):
# # #             n = len(code or '')
# # #             if n <= 8:    return '6pt'
# # #             elif n <= 12: return '5pt'
# # #             else:         return '4pt'
# # #
# # #         # ── Rotated-text cell helper ──────────────────────────────────────────
# # #         # Creates a <td> of width=col_w_mm, height=LH_MM.
# # #         # Inside it places a div that is LH wide × col_w tall, then rotates it
# # #         # -90°, so it becomes col_w wide × LH tall — exactly filling the cell.
# # #         #
# # #         # align='bottom'  → text sits at the BOTTOM edge of the label
# # #         #                   (visually the right/cut edge when reading rotated text)
# # #         # align='center'  → text centred in the column
# # #         def rotated_cell(text, col_w_mm, font_size, extra_style='', align='bottom'):
# # #             col_w = col_w_mm * MM
# # #             # After rotating the inner div by -90°, its top-left corner shifts.
# # #             # We compensate with negative margin so the div stays inside the td.
# # #             shift = (LH - col_w) / 2.0
# # #             transform = (
# # #                 'transform:rotate(-90deg);'
# # #                 '-webkit-transform:rotate(-90deg);'
# # #                 'transform-origin:50% 50%;'
# # #                 '-webkit-transform-origin:50% 50%;'
# # #             )
# # #             # justify-content acts on the PRE-rotation axis (vertical = LH tall).
# # #             # 'flex-end'   → content at bottom of LH  → after -90°: LEFT of label
# # #             # 'flex-start' → content at top of LH     → after -90°: RIGHT of label
# # #             # We want text toward the bottom edge of the label (right after rotate)
# # #             # so use 'flex-start'.
# # #             justify = 'flex-start' if align == 'bottom' else 'center'
# # #             rotated_div = (
# # #                 '<div style="'
# # #                 'width:' + str(round(LH, 2)) + 'px;'
# # #                 'height:' + str(round(col_w, 2)) + 'px;'
# # #                 'display:flex;'
# # #                 'flex-direction:column;'
# # #                 'align-items:center;'
# # #                 'justify-content:' + justify + ';'
# # #                 'overflow:hidden;'
# # #                 'font-size:' + font_size + ';'
# # #                 'font-weight:bold;'
# # #                 'padding:1px 3px;'
# # #                 + extra_style
# # #                 + transform
# # #                 + 'margin-top:' + str(round(-shift, 2)) + 'px;'
# # #                 'margin-left:' + str(round(-shift, 2)) + 'px;'
# # #                 '">' + text + '</div>'
# # #             )
# # #             return (
# # #                 '<td style="'
# # #                 'width:' + str(round(col_w, 2)) + 'px;'
# # #                 'height:' + str(round(LH, 2)) + 'px;'
# # #                 'overflow:hidden;'
# # #                 'padding:0;'
# # #                 'vertical-align:middle;'
# # #                 'text-align:center;">'
# # #                 + rotated_div
# # #                 + '</td>'
# # #             )
# # #
# # #         def one_label(lbl):
# # #             name = lbl['name'] or ''
# # #             code = lbl.get('label_code') or ''
# # #
# # #             # ── Col 1: QR image only (no code below it anymore) ───────────────
# # #             qr_html = ''
# # #             if self.show_qr:
# # #                 qr_html = (
# # #                     '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
# # #                     'style="width:' + px(QR_MM) + ';height:' + px(QR_MM) + ';'
# # #                     'display:block;margin:0 auto;" alt=""/>'
# # #                 )
# # #             col1 = (
# # #                 '<td style="width:' + str(round(QC, 2)) + 'px;'
# # #                 'height:' + str(round(LH, 2)) + 'px;'
# # #                 'vertical-align:middle;text-align:center;'
# # #                 'padding:1px;overflow:hidden;">'
# # #                 + qr_html
# # #                 + '</td>'
# # #             )
# # #
# # #             div0 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
# # #
# # #             # ── Col 2: Product name — rotated, pushed to bottom ───────────────
# # #             def wrap_name(n, chars_per_line=7):
# # #                 words = n.split()
# # #                 lines = []
# # #                 current = ''
# # #                 for w in words:
# # #                     if current and len(current) + 1 + len(w) > chars_per_line:
# # #                         lines.append(current)
# # #                         current = w
# # #                     else:
# # #                         current = (current + ' ' + w).strip()
# # #                 if current:
# # #                     lines.append(current)
# # #                 return '<br/>'.join(lines)
# # #
# # #             wrapped_name = wrap_name(name.upper())
# # #             col2 = rotated_cell(
# # #                 wrapped_name,
# # #                 NAME_COL_MM,
# # #                 _name_font(name),
# # #                 extra_style=(
# # #                     'text-transform:uppercase;'
# # #                     'letter-spacing:0.2px;'
# # #                     'white-space:normal;'
# # #                     'word-break:break-word;'
# # #                     'text-align:center;'
# # #                     'line-height:1.2;'
# # #                 ),
# # #                 align='bottom',
# # #             )
# # #
# # #             div1 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
# # #
# # #             # ── Col 3: Label code — rotated, pushed to bottom ─────────────────
# # #             col3_empty = (
# # #                 '<td style="width:' + str(round(CODE_COL_MM * MM, 2)) + 'px;'
# # #                 'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
# # #             )
# # #             if self.show_label_code and code:
# # #                 col3 = rotated_cell(
# # #                     code,
# # #                     CODE_COL_MM,
# # #                     _code_font(code),
# # #                     extra_style='white-space:nowrap;letter-spacing:0.3px;',
# # #                     align='bottom',
# # #                 )
# # #             else:
# # #                 col3 = col3_empty
# # #
# # #             div2 = '<td style="width:1px;padding:0;border-left:1px dashed #999;"></td>'
# # #
# # #             # ── Col 4: MRP — rotated, pushed to bottom ────────────────────────
# # #             col4_empty = (
# # #                 '<td style="width:' + str(round(MRP_COL_MM * MM, 2)) + 'px;'
# # #                 'height:' + str(round(LH, 2)) + 'px;padding:0;"></td>'
# # #             )
# # #             if self.show_mrp:
# # #                 mrp_text = 'MRP Rs.' + str(lbl['mrp'])
# # #                 col4 = rotated_cell(
# # #                     mrp_text,
# # #                     MRP_COL_MM,
# # #                     '5pt',
# # #                     extra_style='white-space:nowrap;',
# # #                     align='bottom',
# # #                 )
# # #             else:
# # #                 col4 = col4_empty
# # #
# # #             return (
# # #                 '<table style="'
# # #                 'border-collapse:collapse;'
# # #                 'width:' + str(round(LW, 2)) + 'px;'
# # #                 'height:' + str(round(LH, 2)) + 'px;'
# # #                 'border:1.5px solid #888;'
# # #                 'border-radius:' + px(2) + ';'
# # #                 'background:white;'
# # #                 'table-layout:fixed;">'
# # #                 '<tr>' + col1 + div0 + col2 + div1 + col3 + div2 + col4 + '</tr>'
# # #                 '</table>'
# # #             )
# # #
# # #         # ── Page layout: 2 labels per page ───────────────────────────────────
# # #         GAP = COL_GAP_MM * MM
# # #         MAR = L_MAR_MM   * MM
# # #         PH  = (LH_MM + 2) * MM
# # #
# # #         pages_html = []
# # #         i = 0
# # #         while i < len(label_list):
# # #             left  = label_list[i]
# # #             right = label_list[i + 1] if (i + 1) < len(label_list) else None
# # #             i += 2
# # #
# # #             row = (
# # #                 '<tr>'
# # #                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
# # #                 + one_label(left) + '</td>'
# # #                 '<td style="width:' + str(round(GAP, 2)) + 'px;padding:0;border:none;"></td>'
# # #                 '<td style="width:' + str(round(LW, 2)) + 'px;vertical-align:top;padding:0;">'
# # #                 + (one_label(right) if right else '') + '</td>'
# # #                 '</tr>'
# # #             )
# # #
# # #             pages_html.append(
# # #                 '<div style="'
# # #                 'width:' + str(round(PW, 2)) + 'px;'
# # #                 'height:' + str(round(PH, 2)) + 'px;'
# # #                 'padding-top:' + str(round(1 * MM, 2)) + 'px;'
# # #                 'padding-left:' + str(round(MAR, 2)) + 'px;'
# # #                 'page-break-after:always;'
# # #                 'box-sizing:border-box;">'
# # #                 '<table style="'
# # #                 'width:' + str(round(2 * LW + GAP, 2)) + 'px;'
# # #                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
# # #                 + row + '</table></div>'
# # #             )
# # #
# # #         html = (
# # #             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
# # #             '<style>'
# # #             '* { margin:0; padding:0; box-sizing:border-box; }'
# # #             'html, body {'
# # #             "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
# # #             '  background:white;'
# # #             '}'
# # #             '@page { margin:0; size: ' + str(PW_MM) + 'mm ' + str(LH_MM + 2) + 'mm; }'
# # #             '</style></head><body>'
# # #             + ''.join(pages_html)
# # #             + '</body></html>'
# # #         )
# # #         return html, PW_MM, LH_MM + 2
# # #
# # #     # ── Print action ──────────────────────────────────────────────────────────
# # #
# # #     def action_print_labels(self):
# # #         self.ensure_one()
# # #         products = self._get_products()
# # #         if not products:
# # #             raise UserError(_('Please select at least one product.'))
# # #
# # #         label_list = self._get_label_list()
# # #
# # #         if self.label_type == 'small':
# # #             html_content, page_w, page_h = self._build_html_small(label_list)
# # #         else:
# # #             html_content, page_w, page_h = self._build_html_large(label_list)
# # #
# # #         html_path = pdf_path = None
# # #         try:
# # #             with tempfile.NamedTemporaryFile(
# # #                     suffix='.html', delete=False,
# # #                     mode='w', encoding='utf-8') as fh:
# # #                 fh.write(html_content)
# # #                 html_path = fh.name
# # #
# # #             pdf_path = html_path.replace('.html', '.pdf')
# # #
# # #             cmd = [
# # #                 'wkhtmltopdf',
# # #                 '--page-width',    str(page_w) + 'mm',
# # #                 '--page-height',   str(page_h) + 'mm',
# # #                 '--margin-top',    '0',
# # #                 '--margin-bottom', '0',
# # #                 '--margin-left',   '0',
# # #                 '--margin-right',  '0',
# # #                 '--disable-smart-shrinking',
# # #                 '--zoom',          '1',
# # #                 '--dpi',           '203',
# # #                 '--no-stop-slow-scripts',
# # #                 '--encoding',      'UTF-8',
# # #                 html_path,
# # #                 pdf_path,
# # #             ]
# # #             result = subprocess.run(cmd, capture_output=True)
# # #
# # #             if result.returncode not in (0, 1) or not os.path.exists(pdf_path):
# # #                 err = result.stderr.decode('utf-8', errors='replace')
# # #                 raise UserError(
# # #                     _('wkhtmltopdf failed (exit %s):\n%s')
# # #                     % (result.returncode, err)
# # #                 )
# # #
# # #             with open(pdf_path, 'rb') as f:
# # #                 pdf_data = f.read()
# # #
# # #         finally:
# # #             for p in (html_path, pdf_path):
# # #                 if p and os.path.exists(p):
# # #                     try:
# # #                         os.unlink(p)
# # #                     except Exception:
# # #                         pass
# # #
# # #         attachment = self.env['ir.attachment'].create({
# # #             'name': 'Product_Labels.pdf',
# # #             'type': 'binary',
# # #             'datas': base64.b64encode(pdf_data),
# # #             'mimetype': 'application/pdf',
# # #             'res_model': self._name,
# # #             'res_id': self.id,
# # #         })
# # #
# # #         pdf_url = '/web/content/' + str(attachment.id)
# # #         products = self._get_products()
# # #         product_names = ', '.join(products.mapped('name'))
# # #         record_name = product_names[:40] + ('...' if len(product_names) > 40 else '')
# # #
# # #         return {
# # #             'type': 'ir.actions.client',
# # #             'tag': 'product_label_print.open_print_dialog',
# # #             'params': {
# # #                 'pdf_url':       pdf_url,
# # #                 'record_name':   record_name,
# # #                 'label_qty':     self.quantity,
# # #                 'product_count': len(products),
# # #             },
# # #         }
# #
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
# #     label_type = fields.Selection([
# #         ('large', 'Large Label (65x54mm) — GP-1125T Roll'),
# #         ('small', 'Small Label (25x15mm)'),
# #     ], string='Label Size', default='large', required=True)
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
# #     # ── LARGE label HTML builder (65x54mm, GP-1125T roll) ────────────────────
# #     # NOTE: Large label is completely unchanged.
# #
# #     def _build_html_large(self, label_list):
# #         LW      = 65
# #         QR_H    = 26
# #         BOT_H   = 28
# #         LH      = QR_H + BOT_H
# #         QR_SIZE = 18
# #         COL_GAP = 60
# #         ROW_GAP = 4
# #         L_MAR   = 13
# #         PW      = 160
# #
# #         def _name_font_size(name):
# #             n = len(name or '')
# #             if n <= 10:   return 20
# #             elif n <= 15: return 16
# #             elif n <= 22: return 13
# #             else:         return 10
# #
# #         def _code_font_size(code):
# #             n = len(code or '')
# #             if n <= 6:    return 18
# #             elif n <= 10: return 15
# #             else:         return 12
# #
# #         def one_label(lbl):
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
# #                     '<div style="text-align:center;font-size:' + code_fs + ';'
# #                     'font-weight:bold;letter-spacing:0.3mm;margin-top:1mm;'
# #                     'word-break:break-all;overflow:hidden;">'
# #                     + lbl['label_code'] + '</div>'
# #                 )
# #
# #             top_cell = (
# #                 '<tr><td style="height:' + str(QR_H) + 'mm;'
# #                 'padding:3mm 1mm 1mm 5mm;vertical-align:top;'
# #                 'border-bottom:1.5px dashed #aaa;">'
# #                 + qr_html + code_html + '</td></tr>'
# #             )
# #
# #             name    = lbl['name'] or ''
# #             name_fs = str(_name_font_size(name)) + 'pt'
# #             mrp_html = ''
# #             if self.show_mrp:
# #                 mrp_html = (
# #                     '<div style="font-size:14pt;padding-left:4mm;margin-top:1mm;">'
# #                     'MRP Rs. ' + str(lbl['mrp']) + '</div>'
# #                 )
# #
# #             bot_cell = (
# #                 '<tr><td style="height:' + str(BOT_H) + 'mm;'
# #                 'padding-bottom:3mm;padding-left:12mm;padding-right:2mm;'
# #                 'vertical-align:bottom;overflow:hidden;">'
# #                 '<div style="font-size:' + name_fs + ';'
# #                 'text-transform:uppercase;word-break:break-word;'
# #                 'word-wrap:break-word;white-space:normal;line-height:2;'
# #                 'overflow:hidden;">'
# #                 + name + '</div>' + mrp_html + '</td></tr>'
# #             )
# #
# #             return (
# #                 '<table style="border-collapse:collapse;width:' + str(LW) + 'mm;'
# #                 'border:1.5px solid #888;border-radius:3mm;background:white;'
# #                 'table-layout:fixed;">'
# #                 + top_cell + bot_cell + '</table>'
# #             )
# #
# #         page_h = 2 + LH + ROW_GAP + 2
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
# #                 '<div style="width:' + str(PW) + 'mm;height:' + str(page_h) + 'mm;'
# #                 'padding-top:2mm;padding-left:' + str(L_MAR) + 'mm;'
# #                 'page-break-after:always;box-sizing:border-box;">'
# #                 '<table style="width:' + str(2 * LW + COL_GAP) + 'mm;'
# #                 'border-collapse:separate;border-spacing:0;table-layout:fixed;">'
# #                 + row + '</table></div>'
# #             )
# #
# #         html = (
# #             '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
# #             '<style>'
# #             '* { margin:0; padding:0; box-sizing:border-box; }'
# #             'html, body {'
# #             "  font-family: 'Arial Narrow', 'Liberation Sans', Arial, sans-serif;"
# #             '  background: white;'
# #             '  width: ' + str(PW) + 'mm;'
# #             '}'
# #             '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
# #             '</style></head><body>'
# #             + ''.join(pages_html)
# #             + '</body></html>'
# #         )
# #         return html, PW, page_h
# #
# #     # ── SMALL label HTML builder (25x15mm, 2 per row) ─────────────────────────
# #     #
# #     # Physical label: 25mm (feed/long axis) x 15mm (short axis).
# #     # When peeled and read normally the label is landscape (wider than tall).
# #     #
# #     # TWO columns only:
# #     #
# #     #  ┌──────────────┬──────────────────────────────────────┐
# #     #  │              │  PRODUCT NAME  (rotated -90 deg)     │
# #     #  │    [QR]      │  LABEL CODE    (rotated -90 deg)     │
# #     #  │              │  MRP Rs. XXX   (rotated -90 deg)     │
# #     #  └──────────────┴──────────────────────────────────────┘
# #     #      9 mm                    16 mm
# #     #
# #     # All three text lines live inside ONE rotated div so they never clip.
# #     # The rotated div is LH px wide x TC px tall before rotation,
# #     # becoming TC px wide x LH px tall after -90 deg — exactly filling the cell.
# #
# #     def _build_html_small(self, label_list):
# #         MM = 3.7795  # mm -> px
# #
# #         # ── Dimensions (mm) ───────────────────────────────────────────────────
# #         LW_MM = 25.0
# #         LH_MM = 15.0
# #
# #         QR_COL_MM = 8.0
# #         TXT_COL_MM = LW_MM - QR_COL_MM  # 17 mm
# #
# #         QR_SIZE_MM = 7.0
# #
# #         COL_GAP_MM = 8.0
# #         L_MAR_MM = 28.0
# #         PW_MM = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
# #
# #         # Pixel equivalents
# #         LW = LW_MM * MM
# #         LH = LH_MM * MM
# #         QC = QR_COL_MM * MM
# #         TC = TXT_COL_MM * MM
# #         PW = PW_MM * MM
# #
# #         def px(mm):
# #             return str(round(mm * MM, 2)) + 'px'
# #
# #         # ── Font helpers ──────────────────────────────────────────────────────
# #         def _name_font(name):
# #             n = len(name or '')
# #             if n <= 8:
# #                 return '8.5pt'
# #             elif n <= 14:
# #                 return '7pt'
# #             elif n <= 20:
# #                 return '6pt'
# #             else:
# #                 return '5pt'
# #
# #         def _code_font(code):
# #             n = len(code or '')
# #             if n <= 8:
# #                 return '7pt'
# #             elif n <= 12:
# #                 return '6pt'
# #             else:
# #                 return '5pt'
# #
# #         # ── Single label ──────────────────────────────────────────────────────
# #         def one_label(lbl):
# #             name = lbl['name'] or ''
# #             code = lbl.get('label_code') or ''
# #             mrp = lbl.get('mrp', 0)
# #
# #             # Col A — QR image, vertically centred
# #             qr_html = ''
# #             if self.show_qr:
# #                 qr_html = (
# #                         '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
# #                                                                              'style="width:' + px(
# #                     QR_SIZE_MM) + ';height:' + px(QR_SIZE_MM) + ';'
# #                                                                 'display:block;margin:0 auto;" alt=""/>'
# #                 )
# #             col_qr = (
# #                     '<td style="'
# #                     'width:' + str(round(QC, 2)) + 'px;'
# #                                                    'height:' + str(round(LH, 2)) + 'px;'
# #                                                                                    'vertical-align:middle;'
# #                                                                                    'text-align:center;'
# #                                                                                    'padding:1px;'
# #                                                                                    'overflow:hidden;">'
# #                     + qr_html
# #                     + '</td>'
# #             )
# #
# #             divider = (
# #                 '<td style="width:1px;padding:0;'
# #                 'border-left:1.5px dashed #aaa;"></td>'
# #             )
# #
# #             max_w = str(round(LH - 6, 2)) + 'px'
# #             shift = (LH - TC) / 2.0
# #
# #             name_line = ''
# #             if name:
# #                 name_line = (
# #                         '<div style="'
# #                         'font-size:' + _name_font(name) + ';'
# #                                                           'text-transform:uppercase;'
# #                                                           'white-space:normal;'
# #                                                           'word-break:break-word;'
# #                                                           'overflow:hidden;'
# #                                                           'max-width:' + max_w + ';'
# #
# #                                                                                  'line-height:1.25;''margin-top:3px;">'
# #                         + name.upper() + '</div>'
# #                 )
# #
# #             code_line = ''
# #             if self.show_label_code and code:
# #                 code_line = (
# #                         '<div style="'
# #                         'font-size:' + _code_font(code) + ';'
# #                                                           'white-space:normal;'
# #                                                           'word-break:break-all;'
# #                                                           'overflow:hidden;'
# #                                                           'max-width:' + max_w + ';'
# #                                                                                  'margin-top:3px;'
# #                                                                                  'line-height:1.2;">'
# #                         + code + '</div>'
# #                 )
# #
# #             mrp_line = ''
# #             if self.show_mrp:
# #                 mrp_line = (
# #                         '<div style="'
# #                         'font-size:7pt;'
# #                         'white-space:normal;'
# #                         'word-break:break-word;'
# #                         'overflow:hidden;'
# #                         'max-width:' + max_w + ';'
# #                                                'margin-top:3px;'
# #                                                'line-height:1.2;">'
# #                                                'MRP Rs.' + str(mrp) + '</div>'
# #                 )
# #
# #             rotated_div = (
# #                     '<div style="'
# #                     'width:' + str(round(LH, 2)) + 'px;'
# #                                                    'height:' + str(round(TC, 2)) + 'px;'
# #                                                                                    'display:flex;'
# #                                                                                    'flex-direction:column;'
# #                                                                                    'align-items:flex-start;'
# #                                                                                    'justify-content:center;'
# #                                                                                    'overflow:hidden;'
# #                                                                                    'transform:rotate(-90deg);'
# #                                                                                    '-webkit-transform:rotate(-90deg);'
# #                                                                                    'transform-origin:50% 50%;'
# #                                                                                    '-webkit-transform-origin:50% 50%;'
# #                                                                                    'margin-top:' + str(
# #                 round(-shift, 2)) + 'px;'
# #                                     'margin-left:' + str(round(-shift, 2)) + 'px;'
# #                                                                              'padding:0 3px;">'
# #                     + name_line
# #                     + code_line
# #                     + mrp_line
# #                     + '</div>'
# #             )
# #
# #             col_txt = (
# #                     '<td style="'
# #                     'width:' + str(round(TC, 2)) + 'px;'
# #                                                    'height:' + str(round(LH, 2)) + 'px;'
# #                                                                                    'vertical-align:middle;'
# #                                                                                    'text-align:center;'
# #                                                                                    'padding:0;'
# #                                                                                    'overflow:hidden;">'
# #                     + rotated_div
# #                     + '</td>'
# #             )
# #
# #             return (
# #                     '<table style="'
# #                     'border-collapse:collapse;'
# #                     'width:' + str(round(LW, 2)) + 'px;'
# #                                                    'height:' + str(round(LH, 2)) + 'px;'
# #                                                                                    'border:1.5px solid #888;'
# #                                                                                    'border-radius:' + px(1.5) + ';'
# #                                                                                                                 'background:white;'
# #                                                                                                                 'table-layout:fixed;">'
# #                                                                                                                 '<tr>' + col_qr + divider + col_txt + '</tr>'
# #                                                                                                                                                       '</table>'
# #             )
# #
# #         # ── Page layout: 2 labels per page ───────────────────────────────────
# #         GAP = COL_GAP_MM * MM
# #         MAR = L_MAR_MM * MM
# #         PH = (LH_MM + 2) * MM
# #
# #         pages_html = []
# #         i = 0
# #         while i < len(label_list):
# #             left = label_list[i]
# #             right = label_list[i + 1] if (i + 1) < len(label_list) else None
# #             i += 2
# #
# #             row = (
# #                     '<tr>'
# #                     '<td style="width:' + str(round(LW, 2)) + 'px;'
# #                                                               'vertical-align:top;padding:0;">'
# #                     + one_label(left) + '</td>'
# #                                         '<td style="width:' + str(round(GAP, 2)) + 'px;'
# #                                                                                    'padding:0;border:none;"></td>'
# #                                                                                    '<td style="width:' + str(
# #                 round(LW, 2)) + 'px;'
# #                                 'vertical-align:top;padding:0;">'
# #                     + (one_label(right) if right else '') + '</td>'
# #                                                             '</tr>'
# #             )
# #
# #             pages_html.append(
# #                 '<div style="'
# #                 'width:' + str(round(PW, 2)) + 'px;'
# #                                                'height:' + str(round(PH, 2)) + 'px;'
# #                                                                                'padding-top:' + str(
# #                     round(1 * MM, 2)) + 'px;'
# #                                         'padding-left:' + str(round(MAR, 2)) + 'px;'
# #                                                                                'page-break-after:always;'
# #                                                                                'box-sizing:border-box;">'
# #                                                                                '<table style="'
# #                                                                                'width:' + str(
# #                     round(2 * LW + GAP, 2)) + 'px;'
# #                                               'border-collapse:separate;'
# #                                               'border-spacing:0;'
# #                                               'table-layout:fixed;">'
# #                 + row + '</table></div>'
# #             )
# #
# #         html = (
# #                 '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
# #                 '<style>'
# #                 '* { margin:0; padding:0; box-sizing:border-box; }'
# #                 'html, body {'
# #                 "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
# #                 '  background:white;'
# #                 '}'
# #                 '@page { margin:0; size: ' + str(PW_MM) + 'mm '
# #                 + str(LH_MM + 2) + 'mm; }'
# #                                    '</style></head><body>'
# #                 + ''.join(pages_html)
# #                 + '</body></html>'
# #         )
# #         return html, PW_MM, LH_MM + 2
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
# #
# #         if self.label_type == 'small':
# #             html_content, page_w, page_h = self._build_html_small(label_list)
# #         else:
# #             html_content, page_w, page_h = self._build_html_large(label_list)
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
# #                 '--page-width',    str(page_w) + 'mm',
# #                 '--page-height',   str(page_h) + 'mm',
# #                 '--margin-top',    '0',
# #                 '--margin-bottom', '0',
# #                 '--margin-left',   '0',
# #                 '--margin-right',  '0',
# #                 '--disable-smart-shrinking',
# #                 '--zoom',          '1',
# #                 '--dpi',           '203',
# #                 '--no-stop-slow-scripts',
# #                 '--encoding',      'UTF-8',
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
#         ('large', 'Large Label (65x54mm) — GP-1125T Roll'),
#         ('small', 'Small Label (25x15mm)'),
#         ('medium', 'Medium Label (40x25mm)'),
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
#     # ── LARGE label HTML builder (65x54mm, GP-1125T roll) ────────────────────
#     # NOTE: Large label is completely unchanged.
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
#     # ── SMALL label HTML builder (25x15mm, 2 per row) ─────────────────────────
#
#     def _build_html_small(self, label_list):
#         MM = 3.7795  # mm -> px
#
#         LW_MM = 25.0
#         LH_MM = 15.0
#
#         QR_COL_MM  = 8.0
#         TXT_COL_MM = LW_MM - QR_COL_MM  # 17 mm
#
#         QR_SIZE_MM = 15.0
#
#         COL_GAP_MM = 8.0
#         L_MAR_MM   = 28.0
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
#             if n <= 8:    return '8.5pt'
#             elif n <= 14: return '7pt'
#             elif n <= 20: return '6pt'
#             else:         return '5pt'
#
#         def _code_font(code):
#             n = len(code or '')
#             if n <= 8:    return '7pt'
#             elif n <= 12: return '6pt'
#             else:         return '5pt'
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
#                     'display:block;margin:0 auto;" alt="" margin-bottom:5px;/>'
#                 )
#             col_qr = (
#                 '<td style="'
#                 'width:' + str(round(QC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;'
#                 'text-align:center;'
#                 'padding:1px;'
#                 'overflow:hidden;">'
#                 + qr_html
#                 + '</td>'
#             )
#
#             divider = (
#                 '<td style="width:1px;padding:0;'
#                 'border-left:1.5px dashed #aaa;"></td>'
#             )
#
#             max_w = str(round(LH - 6, 2)) + 'px'
#             shift = (LH - TC) / 2.0
#
#             name_line = ''
#             if name:
#                 name_line = (
#                     '<div style="'
#                     'font-size:' + _name_font(name) + ';'
#                     'text-transform:uppercase;'
#                     'white-space:normal;'
#                     'word-break:break-word;'
#                     'overflow:hidden;'
#                     'max-width:' + max_w + ';'
#                     'line-height:1.25;'
#                     'margin-top:3px;">'
#                     + name.upper() + '</div>'
#                 )
#
#             code_line = ''
#             if self.show_label_code and code:
#                 code_line = (
#                     '<div style="'
#                     'font-size:' + _code_font(code) + ';'
#                     'white-space:normal;'
#                     'word-break:break-all;'
#                     'overflow:hidden;'
#                     'max-width:' + max_w + ';'
#                     'margin-top:3px;'
#                     'line-height:1.2;">'
#                     + code + '</div>'
#                 )
#
#             mrp_line = ''
#             if self.show_mrp:
#                 mrp_line = (
#                     '<div style="'
#                     'font-size:7pt;'
#                     'white-space:normal;'
#                     'word-break:break-word;'
#                     'overflow:hidden;'
#                     'max-width:' + max_w + ';'
#                     'margin-top:3px;'
#                     'line-height:1.2;">'
#                     'MRP Rs.' + str(mrp) + '</div>'
#                 )
#
#             rotated_div = (
#                 '<div style="'
#                 'width:' + str(round(LH, 2)) + 'px;'
#                 'height:' + str(round(TC, 2)) + 'px;'
#                 'display:flex;'
#                 'flex-direction:column;'
#                 'align-items:flex-start;'
#                 'justify-content:center;'
#                 'overflow:hidden;'
#                 'transform:rotate(-90deg);'
#                 '-webkit-transform:rotate(-90deg);'
#                 'transform-origin:50% 50%;'
#                 '-webkit-transform-origin:50% 50%;'
#                 'margin-top:' + str(round(-shift, 2)) + 'px;'
#                 'margin-left:' + str(round(-shift, 2)) + 'px;'
#                 'padding:0 3px;">'
#                 + name_line
#                 + code_line
#                 + mrp_line
#                 + '</div>'
#             )
#
#             col_txt = (
#                 '<td style="'
#                 'width:' + str(round(TC, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'vertical-align:middle;'
#                 'text-align:center;'
#                 'padding:0;'
#                 'overflow:hidden;">'
#                 + rotated_div
#                 + '</td>'
#             )
#
#             return (
#                 '<table style="'
#                 'border-collapse:collapse;'
#                 'width:' + str(round(LW, 2)) + 'px;'
#                 'height:' + str(round(LH, 2)) + 'px;'
#                 'border:1.5px solid #888;'
#                 'border-radius:' + px(1.5) + ';'
#                 'background:white;'
#                 'table-layout:fixed;">'
#                 '<tr>' + col_qr + divider + col_txt + '</tr>'
#                 '</table>'
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
#                 '<td style="width:' + str(round(LW, 2)) + 'px;'
#                 'vertical-align:top;padding:0;">'
#                 + one_label(left) + '</td>'
#                 '<td style="width:' + str(round(GAP, 2)) + 'px;'
#                 'padding:0;border:none;"></td>'
#                 '<td style="width:' + str(round(LW, 2)) + 'px;'
#                 'vertical-align:top;padding:0;">'
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
#                 'border-collapse:separate;'
#                 'border-spacing:0;'
#                 'table-layout:fixed;">'
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
#             '@page { margin:0; size: ' + str(PW_MM) + 'mm '
#             + str(LH_MM + 2) + 'mm; }'
#             '</style></head><body>'
#             + ''.join(pages_html)
#             + '</body></html>'
#         )
#         return html, PW_MM, LH_MM + 2
#
#         # ── MEDIUM label HTML builder (40x25mm, 2 per row) ────────────────────────
#         #
#         # Layout (landscape label, read normally):
#         #
#         #  ┌────────────────────────────────────────┐
#         #  │         PRODUCT NAME (centred)         │
#         #  │  ┌──────────────────────────────────┐  │
#         #  │  │  |||||||||| BARCODE |||||||||||  │  │
#         #  │  └──────────────────────────────────┘  │
#         #  │  123456789            MRP Rs.1,00      │
#         #  └────────────────────────────────────────┘
#         #
#         # Uses python-barcode (Code128) rendered as SVG embedded inline.
#         # No QR code, no rotation.
#
#         def _build_html_medium(self, label_list):
#             MM = 3.7795  # mm → px
#
#             LW_MM = 40.0
#             LH_MM = 25.0
#
#             COL_GAP_MM = 6.0
#             L_MAR_MM = 20.0
#             PW_MM = 2 * LW_MM + COL_GAP_MM + 2 * L_MAR_MM
#
#             LW = LW_MM * MM
#             LH = LH_MM * MM
#             PW = PW_MM * MM
#
#             def px(mm):
#                 return str(round(mm * MM, 2)) + 'px'
#
#             # ── Barcode generator (Code128 → base64 PNG) ─────────────────────────
#             def _make_barcode_base64(value):
#                 try:
#                     import barcode as python_barcode
#                     from barcode.writer import ImageWriter
#                     import io as _io
#                     code = python_barcode.get('code128', str(value or 'LABEL'),
#                                               writer=ImageWriter())
#                     buf = _io.BytesIO()
#                     code.write(buf, options={
#                         'module_height': 8.0,  # bar height in mm
#                         'module_width': 0.18,  # narrow bar width in mm
#                         'quiet_zone': 1.0,
#                         'font_size': 5,
#                         'text_distance': 2.0,
#                         'write_text': False,  # we print the number ourselves below
#                         'background': 'white',
#                         'foreground': 'black',
#                         'dpi': 203,
#                     })
#                     return base64.b64encode(buf.getvalue()).decode('ascii')
#                 except Exception:
#                     # 1×1 white pixel fallback
#                     return (
#                         'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC'
#                         'AAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII='
#                     )
#
#             # ── Font helpers ──────────────────────────────────────────────────────
#             def _name_font(name):
#                 n = len(name or '')
#                 if n <= 10:
#                     return '9pt'
#                 elif n <= 18:
#                     return '7.5pt'
#                 elif n <= 26:
#                     return '6pt'
#                 else:
#                     return '5pt'
#
#             def _code_font(code):
#                 n = len(code or '')
#                 if n <= 10:
#                     return '7pt'
#                 elif n <= 16:
#                     return '6pt'
#                 else:
#                     return '5pt'
#
#             # ── Single label ──────────────────────────────────────────────────────
#             def one_label(lbl):
#                 name = lbl['name'] or ''
#                 code = lbl.get('label_code') or ''
#                 mrp = lbl.get('mrp', 0)
#                 bc_value = code or name  # use label_code for barcode if available
#
#                 # ── Name row ─────────────────────────────────────────────────────
#                 name_row = (
#                         '<tr><td colspan="2" style="'
#                         'padding:1.5mm 2mm 0.5mm 2mm;'
#                         'text-align:center;'
#                         'font-size:' + _name_font(name) + ';'
#                                                           'font-weight:bold;'
#                                                           'text-transform:uppercase;'
#                                                           'letter-spacing:0.3px;'
#                                                           'white-space:normal;'
#                                                           'word-break:break-word;'
#                                                           'overflow:hidden;'
#                                                           'line-height:1.2;'
#                                                           'border-bottom:1px dashed #bbb;">'
#                         + name.upper()
#                         + '</td></tr>'
#                 )
#
#                 # ── Barcode row ───────────────────────────────────────────────────
#                 bc_b64 = _make_barcode_base64(bc_value)
#                 barcode_row = (
#                         '<tr><td colspan="2" style="'
#                         'padding:1mm 2mm 0mm 2mm;'
#                         'text-align:center;'
#                         'vertical-align:middle;">'
#                         '<img src="data:image/png;base64,' + bc_b64 + '" '
#                                                                       'style="'
#                                                                       'height:' + px(10) + ';'
#                                                                                            'max-width:' + px(
#                     LW_MM - 4) + ';'
#                                  'display:block;margin:0 auto;" alt=""/>'
#                                  '</td></tr>'
#                 )
#
#                 # ── Bottom row: label code left, MRP right ────────────────────────
#                 code_cell = ''
#                 if self.show_label_code and code:
#                     code_cell = (
#                             '<td style="'
#                             'padding:0.5mm 1mm 1mm 2mm;'
#                             'text-align:left;'
#                             'font-size:' + _code_font(code) + ';'
#                                                               'font-weight:bold;'
#                                                               'white-space:nowrap;'
#                                                               'overflow:hidden;">'
#                             + code
#                             + '</td>'
#                     )
#                 else:
#                     code_cell = '<td></td>'
#
#                 mrp_cell = ''
#                 if self.show_mrp:
#                     mrp_cell = (
#                             '<td style="'
#                             'padding:0.5mm 2mm 1mm 1mm;'
#                             'text-align:right;'
#                             'font-size:8pt;'
#                             'font-weight:bold;'
#                             'white-space:nowrap;'
#                             'overflow:hidden;">'
#                             'MRP Rs.' + str(mrp)
#                             + '</td>'
#                     )
#                 else:
#                     mrp_cell = '<td></td>'
#
#                 bottom_row = (
#                         '<tr>'
#                         + code_cell
#                         + mrp_cell
#                         + '</tr>'
#                 )
#
#                 return (
#                         '<table style="'
#                         'border-collapse:collapse;'
#                         'width:' + str(round(LW, 2)) + 'px;'
#                                                        'height:' + str(round(LH, 2)) + 'px;'
#                                                                                        'border:1.5px solid #888;'
#                                                                                        'border-radius:' + px(2) + ';'
#                                                                                                                   'background:white;'
#                                                                                                                   'table-layout:fixed;">'
#                         + name_row
#                         + barcode_row
#                         + bottom_row
#                         + '</table>'
#                 )
#
#             # ── Page layout: 2 labels per row ─────────────────────────────────────
#             GAP = COL_GAP_MM * MM
#             MAR = L_MAR_MM * MM
#             PH = (LH_MM + 2) * MM
#
#             pages_html = []
#             i = 0
#             while i < len(label_list):
#                 left = label_list[i]
#                 right = label_list[i + 1] if (i + 1) < len(label_list) else None
#                 i += 2
#
#                 row = (
#                         '<tr>'
#                         '<td style="width:' + str(round(LW, 2)) + 'px;'
#                                                                   'vertical-align:top;padding:0;">'
#                         + one_label(left) + '</td>'
#                                             '<td style="width:' + str(round(GAP, 2)) + 'px;'
#                                                                                        'padding:0;border:none;"></td>'
#                                                                                        '<td style="width:' + str(
#                     round(LW, 2)) + 'px;'
#                                     'vertical-align:top;padding:0;">'
#                         + (one_label(right) if right else '') + '</td>'
#                                                                 '</tr>'
#                 )
#
#                 pages_html.append(
#                     '<div style="'
#                     'width:' + str(round(PW, 2)) + 'px;'
#                                                    'height:' + str(round(PH, 2)) + 'px;'
#                                                                                    'padding-top:' + str(
#                         round(1 * MM, 2)) + 'px;'
#                                             'padding-left:' + str(round(MAR, 2)) + 'px;'
#                                                                                    'page-break-after:always;'
#                                                                                    'box-sizing:border-box;">'
#                                                                                    '<table style="'
#                                                                                    'width:' + str(
#                         round(2 * LW + GAP, 2)) + 'px;'
#                                                   'border-collapse:separate;'
#                                                   'border-spacing:0;'
#                                                   'table-layout:fixed;">'
#                     + row + '</table></div>'
#                 )
#
#             html = (
#                     '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
#                     '<style>'
#                     '* { margin:0; padding:0; box-sizing:border-box; }'
#                     'html, body {'
#                     "  font-family: 'Arial Narrow', Arial, Helvetica, sans-serif;"
#                     '  background:white;'
#                     '}'
#                     '@page { margin:0; size: ' + str(PW_MM) + 'mm '
#                     + str(LH_MM + 2) + 'mm; }'
#                                        '</style></head><body>'
#                     + ''.join(pages_html)
#                     + '</body></html>'
#             )
#             return html, PW_MM, LH_MM + 2
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

    product_tmpl_ids = fields.Many2many('product.template')
    product_ids = fields.Many2many('product.product')
    quantity = fields.Integer(default=1, required=True)

    show_mrp = fields.Boolean(default=True)
    show_qr = fields.Boolean(default=True)
    show_label_code = fields.Boolean(default=True)

    label_type = fields.Selection([
        ('large', 'Large'),
        ('small', 'Small'),
        ('medium', 'Medium'),
    ], default='large', required=True)

    # ✅ FIXED QR
    def _make_qr_base64(self, value):
        try:
            import qrcode
            qr = qrcode.QRCode(
                version=2,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(value or 'LABEL')
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return base64.b64encode(buf.getvalue()).decode()
        except Exception:
            return ''

    def _get_products(self):
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    # ✅ FIXED QR DATA
    def _get_label_list(self):
        products = self._get_products()
        label_list = []

        for product in products:
            tmpl = product.product_tmpl_id

            qr_value = (
                product.barcode
                or product.default_code
                or str(product.id)
            )

            qr_b64 = self._make_qr_base64(qr_value)

            for _ in range(self.quantity):
                label_list.append({
                    'name': tmpl.name or '',
                    'label_code': tmpl.default_code or '',
                    'mrp': int(tmpl.list_price or 0),
                    'qr_b64': qr_b64,
                })

        return label_list

    # ✅ FIXED SMALL LABEL
    def _build_html_small(self, label_list):
        MM = 3.7795

        LW_MM = 25
        LH_MM = 15

        QR_SIZE_MM = 12

        def px(mm):
            return str(round(mm * MM, 2)) + 'px'

        def one_label(lbl):
            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + px(QR_SIZE_MM) + ';height:' + px(QR_SIZE_MM) + ';margin:auto;display:block;" />'
                )

            return f"""
            <table style="width:{px(LW_MM)};height:{px(LH_MM)};
            border:1px solid #444;">
                <tr>
                    <td style="width:40%;text-align:center;">{qr_html}</td>
                    <td style="padding:2px;font-size:7pt;">
                        {lbl['name']}<br/>
                        {lbl['label_code']}<br/>
                        Rs.{lbl['mrp']}
                    </td>
                </tr>
            </table>
            """

        html = ''.join([one_label(l) for l in label_list])

        return f"<html><body>{html}</body></html>", 60, 20

    def action_print_labels(self):
        self.ensure_one()

        if not self._get_products():
            raise UserError(_('No products selected'))

        labels = self._get_label_list()

        if self.label_type == 'small':
            html, w, h = self._build_html_small(labels)
        else:
            raise UserError("Only small label handled here")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
            f.write(html.encode())
            html_path = f.name

        pdf_path = html_path.replace('.html', '.pdf')

        cmd = [
            'wkhtmltopdf',
            '--dpi', '300',
            '--image-dpi', '300',
            '--image-quality', '100',
            html_path,
            pdf_path
        ]

        subprocess.run(cmd)

        with open(pdf_path, 'rb') as f:
            pdf = f.read()

        return {
            'type': 'ir.actions.act_url',
            'url': 'data:application/pdf;base64,' + base64.b64encode(pdf).decode(),
            'target': 'new'
        }