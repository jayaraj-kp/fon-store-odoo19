# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── E-Catalogue fields ──────────────────────────────────────────────────
    enable_ecatalogue = fields.Boolean(
        string='Enable E-Catalogue',
        default=False,
        help='Make this product visible in the E-Catalogue.',
    )
    ecatalogue_cover_image = fields.Image(
        string='Cover Image',
        max_width=1920,
        max_height=1920,
    )
    ecatalogue_terms = fields.Html(
        string='Terms & Conditions',
        sanitize=True,
    )
    ecatalogue_image_ids = fields.One2many(
        comodel_name='product.ecatalogue.image',
        inverse_name='product_tmpl_id',
        string='Attached Images',
    )
    ecatalogue_image_count = fields.Integer(
        string='Image Count',
        compute='_compute_ecatalogue_image_count',
    )

    def _compute_ecatalogue_image_count(self):
        for rec in self:
            rec.ecatalogue_image_count = len(rec.ecatalogue_image_ids)
