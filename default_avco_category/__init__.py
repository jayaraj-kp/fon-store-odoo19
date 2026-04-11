# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """
    Write an ir.default record so Odoo's default system
    knows that product.category.property_cost_method = 'average' (AVCO).
    This runs once on module install/upgrade.
    """
    env['ir.default'].set(
        'product.category',
        'property_cost_method',
        'average',
    )
