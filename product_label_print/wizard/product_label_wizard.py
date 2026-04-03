from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import base64


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

    def _get_products(self):
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    def _build_label_html(self, label_list, col_count):
        """Build complete HTML for the label sheet."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        css = """
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; background: white; }
            table.sheet { border-collapse: separate; border-spacing: 0; width: 100%; }
            td.cell {
                border: 1px solid #888;
                width: 73mm;
                height: 28mm;
                padding: 0;
                vertical-align: middle;
            }
            td.gap { width: 2mm; border: none; padding: 0; }
            tr.row-gap { height: 1mm; }
            table.inner { border-collapse: collapse; width: 100%; height: 28mm; }
            td.qr-td { width: 26mm; text-align: center; vertical-align: middle; padding: 1mm; }
            td.code-td { width: 7mm; text-align: center; vertical-align: middle; padding: 0; }
            .code-text {
                display: inline-block;
                writing-mode: vertical-rl;
                transform: rotate(180deg);
                font-size: 5pt;
                font-weight: bold;
                white-space: nowrap;
            }
            td.info-td { vertical-align: bottom; padding: 1mm 1mm 2mm 1mm; }
            .pname { font-size: 6pt; font-weight: bold; text-transform: uppercase; display: block; line-height: 1.4; }
            .mrp { font-size: 5.5pt; display: block; margin-top: 1mm; }
        </style>
        """

        rows = []
        for i in range(0, len(label_list), col_count):
            rows.append(label_list[i:i + col_count])

        html_rows = []
        for r_idx, row in enumerate(rows):
            cells = []
            for c_idx, lbl in enumerate(row):
                qr_url = '{}/report/barcode/QR/{}?width=70&height=70'.format(
                    base_url,
                    lbl['qr_value'].replace('&', '%26').replace(' ', '%20')
                )

                inner_cells = ''
                if self.show_qr:
                    inner_cells += '<td class="qr-td"><img src="{}" style="width:24mm;height:24mm;" alt="QR"/></td>'.format(qr_url)
                if self.show_label_code and lbl.get('label_code'):
                    inner_cells += '<td class="code-td"><span class="code-text">{}</span></td>'.format(lbl['label_code'])
                inner_cells += '<td class="info-td"><span class="pname">{}</span>{}</td>'.format(
                    lbl['name'],
                    '<span class="mrp">MRP Rs&nbsp;&nbsp;{}</span>'.format(lbl['mrp']) if self.show_mrp else ''
                )

                cell_html = '<td class="cell"><table class="inner"><tr>{}</tr></table></td>'.format(inner_cells)
                cells.append(cell_html)
                if c_idx < len(row) - 1:
                    cells.append('<td class="gap"></td>')

            html_rows.append('<tr>{}</tr>'.format(''.join(cells)))
            if r_idx < len(rows) - 1:
                html_rows.append('<tr class="row-gap"><td></td></tr>')

        html = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/>{}</head>
<body>
<table class="sheet">{}</table>
</body>
</html>""".format(css, ''.join(html_rows))

        return html

    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        label_list = []
        for product in products:
            tmpl = product.product_tmpl_id
            label_code = getattr(tmpl, 'label_code', None) or product.default_code or ''
            mrp = int(tmpl.list_price or 0)
            qr_value = product.barcode or product.default_code or tmpl.name or str(product.id)
            for _i in range(self.quantity):
                label_list.append({
                    'name': tmpl.name or '',
                    'label_code': label_code or '',
                    'mrp': mrp,
                    'qr_value': qr_value or 'LABEL',
                })

        col_count = int(self.columns)
        html_content = self._build_label_html(label_list, col_count)

        # Use wkhtmltopdf directly via Odoo's rendering
        from odoo.tools import pdf as pdf_tools
        import subprocess
        import tempfile
        import os

        # Write HTML to temp file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
            f.write(html_content)
            html_path = f.name

        pdf_path = html_path.replace('.html', '.pdf')

        try:
            # Page size: 150mm wide x 30mm tall per row
            page_h = max(30, 30 * ((len(label_list) + col_count - 1) // col_count))
            cmd = [
                'wkhtmltopdf',
                '--page-width', '150mm',
                '--page-height', '{}mm'.format(page_h),
                '--margin-top', '0mm',
                '--margin-bottom', '0mm',
                '--margin-left', '0mm',
                '--margin-right', '0mm',
                '--disable-smart-shrinking',
                '--zoom', '1',
                html_path,
                pdf_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)

            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
        finally:
            try:
                os.unlink(html_path)
                os.unlink(pdf_path)
            except Exception:
                pass

        # Return the PDF as a download
        attachment = self.env['ir.attachment'].create({
            'name': 'Product_Labels.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_data),
            'mimetype': 'application/pdf',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'new',
        }
