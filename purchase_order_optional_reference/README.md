# Purchase Order Optional Fields Module

## Overview
This custom Odoo module makes **two critical fields** optional in the **Purchase Order** system:
1. **Purchase Order**: Order Reference field (`name`)
2. **Purchase Order Lines**: Description field (`name`)

This is useful when importing purchase orders and order line items that don't have these values yet.

## Problems Solved
By default, Odoo makes both these fields mandatory. This module changes them to optional, allowing you to:
- Import purchase orders without providing an Order Reference
- Import purchase order line items without product descriptions
- Create orders and lines programmatically without these fields
- Set these values later if needed

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
   - In Apps, search for "Purchase Order Optional Fields"
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

#### 1. Purchase Order (`purchase.order.name`)
- **Field**: Order Reference (name)
- **Before**: `required=True` (mandatory)
- **After**: `required=False` (optional)
- **Impact**: Allows importing POs without requiring a reference

#### 2. Purchase Order Line (`purchase_order_line.name`)
- **Field**: Description (name)
- **Before**: `required=True` (mandatory)
- **After**: `required=False` (optional)
- **Impact**: Allows importing line items without requiring product descriptions

## Testing

After installation, you should be able to:

1. **Import Purchase Orders** without the "Order Reference" column
2. **Import Purchase Order Lines** without product descriptions
3. **Create Purchase Orders** programmatically without a name value
4. **Create Order Lines** without requiring descriptions
5. **Update existing imports** that were failing due to missing Order Reference or Line Descriptions

## Compatibility

- **Odoo Version:** 14.0+
- **Dependencies:** purchase (standard Odoo module)
- **License:** LGPL-3

## Uninstallation

To remove this module:

1. Go to **Apps**
2. Search for "Purchase Order Optional Fields"
3. Click the module
4. Click "Uninstall"

## Support

If you encounter any issues:

1. Check the Odoo logs: `/var/log/odoo/odoo.log`
2. Ensure the module folder is in the correct location
3. Verify you've updated the apps list after copying the folder
4. Make sure Odoo has been restarted after folder placement

## Additional Notes

- This module modifies the `name` field requirement in both:
  - `purchase.order` (Order Reference)
  - `purchase_order_line` (Description)
- It does not affect any other Purchase Order functionality
- The module is compatible with other purchase modules
- Auto-increment sequences still work normally
- Product associations are not affected by this change

---

**Created:** 2026
**Module Name:** purchase_order_optional_reference
**Version:** 1.0
