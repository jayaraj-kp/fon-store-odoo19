from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductLabelWizard(models.TransientModel):
    _name = 'product.label.wizard'
    _description = 'Product Label Printing Wizard'

    product_tmpl_ids = fields.Many2many(
        'product.template',
        string='Product Templates',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Product Variants',
    )
    quantity = fields.Integer(
        string='Number of Labels per Product',
        default=1,
        required=True,
    )
    # Label paper size for GP-1125T
    label_width_mm = fields.Integer(
        string='Label Width (mm)',
        default=75,
        help='Label width in mm. GP-1125T supports 20-120mm.',
    )
    label_height_mm = fields.Integer(
        string='Label Height (mm)',
        default=30,
        help='Label height in mm.',
    )
    columns = fields.Selection(
        [('1', '1 Column'), ('2', '2 Columns')],
        string='Columns per Row',
        default='2',
        required=True,
    )
    show_mrp = fields.Boolean(string='Show MRP', default=True)
    show_qr = fields.Boolean(string='Show QR Code', default=True)
    show_label_code = fields.Boolean(string='Show Label Code (e.g. KC110)', default=True)

    # Computed label lines for the report
    label_line_ids = fields.One2many(
        'product.label.line',
        'wizard_id',
        string='Label Lines',
        compute='_compute_label_lines',
        store=False,
    )

    @api.depends('product_tmpl_ids', 'product_ids', 'quantity')
    def _compute_label_lines(self):
        for wizard in self:
            lines = []
            products = wizard._get_products()
            for product in products:
                for _i in range(wizard.quantity):
                    lines.append({
                        'product_id': product.id,
                    })
            wizard.label_line_ids = [(5, 0, 0)] + [(0, 0, l) for l in lines]

    def _get_products(self):
        """Return product.product records to print labels for."""
        products = self.env['product.product']
        if self.product_ids:
            products |= self.product_ids
        if self.product_tmpl_ids:
            for tmpl in self.product_tmpl_ids:
                products |= tmpl.product_variant_ids
        return products

    def action_print_labels(self):
        """Generate and return the label PDF report."""
        self.ensure_one()
        products = self._get_products()
        if not products:
            raise UserError(_('Please select at least one product to print labels for.'))

        # Build label data: list of dicts, repeated by quantity
        label_data = []
        for product in products:
            tmpl = product.product_tmpl_id
            # Determine label code: use label_code field, else internal ref, else product code
            label_code = (
                getattr(tmpl, 'label_code', None)
                or product.default_code
                or ''
            )
            # MRP: use list price
            mrp = tmpl.list_price

            # QR code value: use barcode if available, else internal ref, else product name
            qr_value = (
                product.barcode
                or product.default_code
                or tmpl.name
                or str(product.id)
            )

            for _i in range(self.quantity):
                label_data.append({
                    'product': product,
                    'name': tmpl.name,
                    'label_code': label_code,
                    'mrp': mrp,
                    'qr_value': qr_value,
                    'barcode': product.barcode or '',
                })

        report_action = self.env.ref(
            'product_label_print.action_product_label_report'
        )
        return report_action.report_action(self, data={
            'label_data': [
                {
                    'name': d['name'],
                    'label_code': d['label_code'],
                    'mrp': d['mrp'],
                    'qr_value': d['qr_value'],
                    'barcode': d['barcode'],
                    'product_id': d['product'].id,
                }
                for d in label_data
            ],
            'columns': int(self.columns),
            'label_width_mm': self.label_width_mm,
            'label_height_mm': self.label_height_mm,
            'show_mrp': self.show_mrp,
            'show_qr': self.show_qr,
            'show_label_code': self.show_label_code,
        })


class ProductLabelLine(models.TransientModel):
    _name = 'product.label.line'
    _description = 'Product Label Line'

    wizard_id = fields.Many2one('product.label.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Product')
