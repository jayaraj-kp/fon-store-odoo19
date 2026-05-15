{
    'name': 'Remove Search Favorites',
    'version': '1.0',
    'category': 'Web',
    'summary': 'Remove the Favorites menu from the search bar',
    'description': 'This module removes the Favorites tab/menu from the search bar dropdown.',
    'depends': ['web'],
    'data': [
        'data/data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'favorites/static/src/css/favorites.css',
            'favorites/static/src/xml/favorites.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
