{
    "name": "Odoo Enterprise Theme",
    "version": "19.0.0.2",
    "summary": "Enterprise-style theme for Odoo 19 Community Edition",
    "author": "fl1 sro",
    "license": "AGPL-3",
    "depends": ["web"],
    "category": "Branding",
    "assets": {
        "web.assets_backend": [
            "/enterprise_theme_mod/static/src/scss/backend_theme.scss",
        ],
        "web.assets_web": [
            "/enterprise_theme_mod/static/src/scss/backend_theme.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": True,
    "images": ["static/description/icon.png"],
}
