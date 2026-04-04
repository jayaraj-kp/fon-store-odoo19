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
        COL_GAP = 55   # gap between 2 label columns
        ROW_GAP = 4     # gap between label rows
        L_MAR   = 5     # fixed left margin
        PW      = 160   # page/roll width mm (wider to fit the gap)

        def one_label(lbl):
            # ── Top cell: QR centered, KC110 below QR ──
            qr_html = ''
            if self.show_qr:
                qr_html = (
                    '<img src="data:image/png;base64,' + lbl['qr_b64'] + '" '
                    'style="width:' + str(QR_SIZE) + 'mm;height:' + str(QR_SIZE) + 'mm;'
                    'display:block;margin:0 auto;" alt=""/>'
                )

            code_html = ''
            if self.show_label_code and lbl.get('label_code'):
                code_html = (
                    '<div style="'
                    'text-align:center;'
                    'font-size:10pt;font-weight:bold;'
                    'letter-spacing:0.5mm;'
                    'margin-top:1.5mm;'
                    '">'
                    + lbl['label_code'] +
                    '</div>'
                )

            top_cell = (
                '<tr><td style="'
                'height:' + str(QR_H) + 'mm;'
                'padding:5mm 1mm 1mm 1mm;'
                'vertical-align:middle;'
                'text-align:center;'
                'border-bottom:1.5px dashed #aaa;'
                '">'
                + qr_html + code_html +
                '</td></tr>'
            )

            # ── Bottom cell: product name + MRP centered ──
            mrp_html = ''
            if self.show_mrp:
                mrp_html = (
                    '<div style="font-size:12pt;font-weight:bold;text-align:center;">'
                    'MRP Rs. ' + str(lbl['mrp']) + '</div>'
                )

            bot_cell = (
                '<tr><td style="'
                'height:' + str(BOT_H) + 'mm;'
                'padding-top:10mm;'
               
                'vertical-align:middle;'
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

        # ── Build pages: 2 labels per page (1 pair per page) ───────────────
        # Each page = exactly 1 row of 2 labels.
        # This means: if user selects 4 labels → 2 pages in PDF.
        # Browser prints all pages with Copies=1 → all labels print correctly.
        # No need to change Copies in browser print dialog.

        page_h = 2 + LH + ROW_GAP + 2   # fixed: 1 row per page

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
                '<div style="'
                'width:' + str(PW) + 'mm;'
                'height:' + str(page_h) + 'mm;'
                'padding-top:2mm;'
                'padding-left:' + str(L_MAR) + 'mm;'
                'page-break-after:always;'
                'box-sizing:border-box;'
                '">'
                '<table style="'
                'width:' + str(2 * LW + COL_GAP) + 'mm;'
                'border-collapse:separate;'
                'border-spacing:0;'
                'table-layout:fixed;">'
                + row +
                '</table>'
                '</div>'
            )

        html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"/>'
            '<style>'
            '* { margin:0; padding:0; box-sizing:border-box; }'
            'html, body {'
            '  font-family: Arial, Helvetica, sans-serif;'
            '  background: white;'
            '  width: ' + str(PW) + 'mm;'
            '}'
            '@page { margin:0; size: ' + str(PW) + 'mm ' + str(page_h) + 'mm; }'
            '</style></head>'
            '<body>'
            + ''.join(pages_html) +
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

