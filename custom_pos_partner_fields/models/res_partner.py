from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    gstin = fields.Char(
        string='GSTIN',
        size=15,
        help='Goods and Services Tax Identification Number',
    )