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
            # Variables must load FIRST, before any other SCSS
            ("prepend", "/enterprise_theme_mod/static/src/scss/primary_variables_custom.scss"),
            "/enterprise_theme_mod/static/src/scss/backend_theme.scss",
        ],
    },
    "installable": True,
    "auto_install": False,
    "application": True,
    "images": ["static/description/icon.png"],
}