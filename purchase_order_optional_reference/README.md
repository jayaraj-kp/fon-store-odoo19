# Purchase Order Optional Reference Module

## Overview
This custom Odoo module makes the **Order Reference** field optional in the **Purchase Order** model. This is useful when importing purchase orders that don't have a reference value yet.

## Problem Solved
By default, Odoo makes the `name` (Order Reference) field mandatory in the Purchase Order model. This module changes it to optional, allowing you to:
- Import purchase orders without providing an Order Reference
- Create purchase orders programmatically without a reference
- Set the reference later if needed

## Installation

### Method 1: Manual Installation

1. **Download the module** and extract it
2. **Copy the folder** to your Odoo addons directory:
   ```
   /path/to/odoo/addons/purchase_order_optional_reference/
   ```
   
   Common locations:
   - Linux: `/opt/odoo/addons/`
   - macOS: `~/odoo/addons/`
   - Windows: `C:\odoo\addons\`

3. **Restart Odoo service:**
   ```bash
   sudo systemctl restart odoo
   ```

4. **Update Apps List** in Odoo:
   - Go to Apps
   - Click the Settings icon (⚙️) at top right
   - Click "Update Apps List"
   - Wait for the update to complete

5. **Install the Module:**
   - In Apps, search for "Purchase Order Optional Reference"
   - Click the module
   - Click "Install"

### Method 2: Via FTP/SFTP
1. Connect to your server via FTP
2. Navigate to `/addons/` folder
3. Upload the `purchase_order_optional_reference` folder
4. Follow steps 3-5 from Method 1

## What This Module Does

### File Structure
```
purchase_order_optional_reference/
├── __init__.py                    # Module init file
├── __manifest__.py                # Module configuration & metadata
├── models/
│   ├── __init__.py
│   └── purchase_order.py          # Main model override
└── views/
    └── purchase_order_views.xml   # View modifications (optional)
```

### Key Changes
The module overrides the `name` field in `purchase.order` model:
- **Before:** `required=True` (mandatory)
- **After:** `required=False` (optional)

## Testing

After installation, you should be able to:

1. **Import Purchase Orders** without the "Order Reference" column
2. **Create Purchase Orders** programmatically without a name value
3. **Update existing imports** that were failing due to missing Order Reference

## Compatibility

- **Odoo Version:** 14.0+
- **Dependencies:** purchase (standard Odoo module)
- **License:** LGPL-3

## Uninstallation

To remove this module:

1. Go to **Apps**
2. Search for "Purchase Order Optional Reference"
3. Click the module
4. Click "Uninstall"

## Support

If you encounter any issues:

1. Check the Odoo logs: `/var/log/odoo/odoo.log`
2. Ensure the module folder is in the correct location
3. Verify you've updated the apps list after copying the folder
4. Make sure Odoo has been restarted after folder placement

## Additional Notes

- This module only modifies the `name` field requirement
- It does not affect any other Purchase Order functionality
- The module is compatible with other purchase modules
- Auto-increment sequences still work normally

---

**Created:** 2026
**Module Name:** purchase_order_optional_reference
**Version:** 1.0
