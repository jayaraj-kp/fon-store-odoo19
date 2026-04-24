# -*- coding: utf-8 -*-
{
    'name': 'Fix Custom Filter (domainFromTree)',
    'version': '19.0.1.0.0',
    'summary': 'Fixes TypeError: domainFromTree is not a function in Custom Filters',
    'description': """
        Patches the missing/broken domainFromTree export that causes all
        Custom Filter options to throw:
            TypeError: domainFromTree is not a function
            at domainFromTreeDateRange (web.assets_web.min.js)
            at DomainSelector.update
            at TreeEditor.notifyChanges / updateNode
    """,
    'category': 'Technical',
    'author': 'Custom',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'fix_custom_filter/static/src/fix_domain_from_tree.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
