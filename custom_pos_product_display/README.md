# POS Product Display - Remove Internal Reference

## Description
This custom module removes the internal reference codes (like [031SPRAY], [044SPRAY], etc.) from product display in Odoo 19 CE Point of Sale module.

## Features
- ✅ Removes internal reference code prefix from product names in POS
- ✅ Works with all POS screens
- ✅ Clean display showing only product names
- ✅ Compatible with Odoo 19 CE

## Installation Steps

### 1. Download and Extract Module
- Download this module folder to your local machine
- The folder should be named: `custom_pos_product_display`

### 2. Copy to Odoo Addons Directory
Copy the entire `custom_pos_product_display` folder to your Odoo addons directory:

**Linux/Mac:**
```bash
cp -r custom_pos_product_display /path/to/odoo/addons/
```

**Windows:**
```
Copy the folder to: C:\Program Files\Odoo\addons\
or
C:\Users\YourUsername\AppData\Local\Odoo\addons\
```

### 3. Update Add-ons in Odoo

1. **Log in to Odoo** as Administrator
2. Go to **Apps** menu
3. Click **Update Apps List** (top-right button)
4. Search for **"POS Product Display"** or **"Remove Internal Reference"**
5. Click **Install** button
6. Wait for the installation to complete

### 4. Restart POS Session
1. Go to **Point of Sale → Sessions**
2. Close any active POS sessions or refresh the browser
3. Open a new POS session
4. Products will now display without internal reference codes

## File Structure
```
custom_pos_product_display/
├── __init__.py                 # Module initialization
├── __manifest__.py             # Module configuration
├── models/
│   ├── __init__.py
│   └── product.py             # Product model override
└── static/src/js/
    └── product_display.js     # POS JavaScript customization
```

## What Changes
**Before:**
```
[031SPRAY] SPRAY ENCHANTEUR ROMANTIC
[044SPRAY] PERFUME SPRAY JASS 60ML
[084EYESHADOW] EYE SHADOW PALETTE GRA
```

**After:**
```
SPRAY ENCHANTEUR ROMANTIC
PERFUME SPRAY JASS 60ML
EYE SHADOW PALETTE GRA
```

## Troubleshooting

### Module doesn't appear in Apps list
- Go to **Settings → Technical → Apps & Updates → Apps**
- Click **Update Apps List** again
- Refresh the page
- Search again

### Changes not visible in POS
- Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
- Close and reopen the POS session
- Restart Odoo services (if using server)

### Database update required
The module automatically updates the database. If you see a popup, click **Update** to apply changes.

## Uninstallation
To remove this module:
1. Go to **Apps**
2. Search for **"POS Product Display"**
3. Click the module
4. Click **Uninstall** button

## Support
For issues or customizations, you can:
- Check your Odoo logs for errors
- Verify that the module folder permissions are correct
- Ensure your Odoo version is 19.0 CE

## License
This module is provided as-is for Odoo 19 CE.

---
**Version:** 19.0.1.0.0
**Odoo Version:** 19.0 CE
