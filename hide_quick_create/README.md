# hide_quick_create

## Purpose
Hides the **"Create [product]"** and **"Create and edit..."** dropdown options that appear when typing in the `product_id` field on:
- Purchase Orders / Requests for Quotation
- Sale Orders

## Installation

1. Copy the `hide_quick_create` folder into your Odoo addons directory:
   ```
   /path/to/odoo/custom_addons/hide_quick_create/
   ```

2. Restart your Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u hide_quick_create
   ```

3. In Odoo, go to:
   **Settings → Apps → Update Apps List**

4. Search for **"Hide Quick Create on Product Fields"** and click **Install**.

## What It Does

| Field | Before | After |
|-------|--------|-------|
| Product (Purchase) | Shows "Create" + "Create and edit..." | Only existing products shown |
| Product (Sale) | Shows "Create" + "Create and edit..." | Only existing products shown |

## Compatibility
- Odoo 19 Community Edition
- Depends on: `purchase`, `sale`
