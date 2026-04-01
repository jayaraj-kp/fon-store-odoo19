{
    "name": "Odoo Enterprise Theme",
    "version": "19.0.0.1",
    "summary": "Enterprise-style theme for Odoo 19 Community Edition",
    "author": "fl1 sro",
    "license": "AGPL-3",
    "maintainer": "Fl1",
    "company": "Fl1 sro",
    "website": "https://fl1.cz",
    "depends": [
        "web",
    ],
    "category": "Branding",
    "description": """
        Enterprise-style Theme for Odoo 19 Community Edition.
        Provides a purple/mauve home menu background with colored app icons,
        matching the Enterprise look and feel.
    """,
    "assets": {
        "web._assets_primary_variables": [
            "/enterprise_theme_mod/static/src/scss/primary_variables_custom.scss",
        ],
        "web.assets_backend": [
            "/enterprise_theme_mod/static/src/scss/backend_theme.scss",
        ],
    },
    "price": 0,
    "currency": "EUR",
    "installable": True,
    "auto_install": False,
    "application": True,
    "images": ["static/description/icon.png"],
}
