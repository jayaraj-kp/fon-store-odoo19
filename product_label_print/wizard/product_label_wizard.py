from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json


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
    label_data_json = fields.Text(string='Label Data JSON', default='[]')

    def _parse_label_data(self):
        """Return flat list of label dicts."""
        self.ensure_one()
        try:
            return json.loads(self.label_data_json or '[]')
        except Exception:
            return []

    def _get_label_rows(self):
        """Return labels grouped into rows based on columns setting.
        Each row is a list of label dicts.
        Called from QWeb template.
        """
        self.ensure_one()
        labels = self._parse_label_data()
        col_count = int(self.columns)
        rows = []
        for i in range(0, len(labels), col_count):
            rows.append(labels[i:i + col_count])
        return rows

    def _get_products(self):
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    def action_print_labels(self):
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product.'))

        label_list = []
        for product in products:
            tmpl = product.product_tmpl_id
            label_code = getattr(tmpl, 'label_code', None) or product.default_code or ''
            mrp = tmpl.list_price or 0
            qr_value = product.barcode or product.default_code or tmpl.name or str(product.id)
            for _i in range(self.quantity):
                label_list.append({
                    'name': tmpl.name or '',
                    'label_code': label_code or '',
                    'mrp': int(mrp),
                    'qr_value': qr_value or 'LABEL',
                })

        self.label_data_json = json.dumps(label_list)
        return self.env.ref('product_label_print.action_product_label_report').report_action(self)
