# -*- coding: utf-8 -*-
{
    'name': 'Default AVCO Costing Method for Product Category',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Sets Average Cost (AVCO) as the default costing method when creating a new product category.',
    'description': """
        This module overrides the default costing method on product categories
        from 'Standard Price' to 'Average Cost (AVCO)' so that every new
        category is pre-filled with AVCO without any manual selection.
    """,
    'author': 'Custom',
    'depends': ['stock'],          # 'stock' provides product.category costing fields
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
