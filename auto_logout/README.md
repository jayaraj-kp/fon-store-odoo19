# Auto Logout - Odoo 19 CE Custom Module

Automatically logs out inactive users after a configurable timeout period.

---

## Features

- ✅ Configurable timeout from **Settings → General Settings**
- ✅ Warning banner shown **1 minute before** logout
- ✅ Timer resets on any user activity (mouse, keyboard, scroll, click)
- ✅ Full-screen overlay message before redirect
- ✅ Set timeout to **0** to completely disable auto logout
- ✅ Works with Odoo 19 Community Edition

---

## Installation

1. Copy the `auto_logout` folder into your Odoo addons directory:
   ```
   /path/to/odoo/addons/auto_logout/
   ```

2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf
   ```

3. Enable **Developer Mode**:
   - Go to **Settings → Activate Developer Mode**

4. Update the apps list:
   - Go to **Apps → Update Apps List**

5. Search for **"Auto Logout"** and click **Install**

---

## Configuration

1. Go to **Settings → General Settings**
2. Scroll to the **Auto Logout** section
3. Set the desired timeout in **minutes** (default: 10)
4. Click **Save**

---

## How It Works

| Component | Description |
|---|---|
| `models/res_config_settings.py` | Adds `auto_logout_delay` field stored in `ir.config_parameter` |
| `controllers/main.py` | JSON-RPC endpoint `/auto_logout/config` to serve config to frontend |
| `static/src/js/auto_logout.js` | Frontend service that tracks inactivity and triggers logout |
| `views/res_config_settings_views.xml` | Adds the setting field to General Settings UI |

---

## Module Structure

```
auto_logout/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── res_config_settings.py
├── controllers/
│   ├── __init__.py
│   └── main.py
├── static/
│   └── src/
│       └── js/
│           └── auto_logout.js
└── views/
    └── res_config_settings_views.xml
```

---

## License

LGPL-3
