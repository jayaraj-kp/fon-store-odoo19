{
    'name': 'Sale Auto Manufacture',
    'version': '19.0.1.0.0',
    'summary': 'Automatically produce Manufacturing Orders when Sale Order is confirmed',
    'description': '''
        When a Sale Order is confirmed:
        - Automatically creates a Manufacturing Order for products with a BoM
        - Automatically confirms and produces the MO
        - Components are consumed (stock reduced)
        - Finished product stock is increased
        No manual intervention needed.
    ''',
    'author': 'Custom',
    'category': 'Manufacturing',
    'depends': [
        'sale_management',
        'mrp',
        'stock',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
