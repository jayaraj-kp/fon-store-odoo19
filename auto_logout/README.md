# Auto Logout — Odoo 19 CE

Automatically logs out inactive users after a configurable timeout.

## What Changed in v3
- **No longer inherits res.config.settings** (which caused xpath errors)
- Uses its own dedicated model `auto.logout.config`
- Settings accessible via: **Settings → Technical → Auto Logout Settings**

## Installation

1. Copy `auto_logout/` to `/opt/odoo19/custom_addons/`
2. Restart Odoo: `sudo systemctl restart odoo`
3. Enable Developer Mode: Settings → Activate Developer Mode
4. Update Apps List: Apps → Update Apps List
5. Install "Auto Logout"

## Configure

Go to **Settings → Technical → Auto Logout Settings**
- Set timeout in minutes (default: 10)
- Click **Save Settings**
- Set to 0 to disable

## License
LGPL-3
