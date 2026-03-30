{
    'name': 'Sale Analytic Distribution Default',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Shows Analytic Distribution column by default in Sale Order lines',
    'description': """
        This module makes the Analytic Distribution field visible by default
        in the Sale Order lines (Order Lines tab) without needing to manually
        enable it via the optional columns toggle.
    """,
    'author': 'Custom',
    'depends': ['sale_management', 'analytic'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_install_hook',
}
