from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    label_code = fields.Char(
        string='Label Code',
        help='Short code printed on label (e.g. KC110). If empty, uses internal reference.',
    )

    def action_print_labels(self):
        """Open label printing wizard from product form."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Product Labels',
            'res_model': 'product.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_ids': [(6, 0, self.ids)],
            },
        }


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_print_labels(self):
        """Open label printing wizard from product variant form."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Product Labels',
            'res_model': 'product.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_ids': [(6, 0, self.ids)],
            },
        }
