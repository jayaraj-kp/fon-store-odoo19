# Auto Logout — Odoo 19 CE Custom Module

Automatically logs out inactive users after a configurable timeout period.

---

## Features

- ✅ Configurable timeout from **Settings → General Settings**
- ✅ Warning banner shown **1 minute before** logout
- ✅ Timer resets on any user activity (mouse, keyboard, scroll, click)
- ✅ Full-screen overlay before redirect to login
- ✅ Set timeout to **0** to completely disable
- ✅ Compatible with **Odoo 19 Community Edition**

---

## Installation

1. Copy the `auto_logout` folder into your Odoo custom addons directory:
   ```
   cp -r auto_logout /opt/odoo19/custom_addons/
   ```

2. Make sure the path is in your `odoo.conf`:
   ```ini
   addons_path = /opt/odoo19/odoo19/addons,/opt/odoo19/custom_addons
   ```

3. Restart Odoo:
   ```bash
   sudo systemctl restart odoo
   ```

4. Enable **Developer Mode**: Settings → Activate Developer Mode

5. Update apps list: Apps → Update Apps List

6. Search for **"Auto Logout"** → Install

---

## Configuration

**Settings → General Settings → Auto Logout**
- Set the number of minutes → Save
- Default: 10 minutes
- Set to 0 to disable

---

## Troubleshooting

If you see an xpath error on install, ensure you are on Odoo 19 and that
`base_setup.res_config_settings_view_form` exists by running in a shell:

```bash
python odoo-bin shell -c odoo.conf -d YOUR_DB
>>> env['ir.ui.view'].search([('xml_id', 'like', 'base_setup.res_config_settings_view_form')])
```

---

## License

LGPL-3
