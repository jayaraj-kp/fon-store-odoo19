# User Access & Restrictions — Odoo 19 CE Custom Module

## Overview
Adds an **"Access & Restrictions"** tab to the `res.users` form view.
Administrators can toggle restrictions per user without creating new groups.

---

## Features

### 🏷️ Product Field Restrictions
| Checkbox | Effect |
|---|---|
| Hide Cost Price | User sees `0.0` / blank for `standard_price` |
| Restrict Cost Price Edit | User cannot save changes to `standard_price` |
| Hide Sales Price | User sees blank for `list_price` |
| Restrict Sales Price Edit | User cannot save changes to `list_price` |
| Hide Barcode | `barcode` field hidden in product form |
| Hide Internal Reference | `default_code` field hidden in product form |
| Hide Tax Fields | `taxes_id` / `supplier_taxes_id` hidden |
| Hide Product Margin | Margin information hidden |

### 📊 Accounting Reports Restrictions
| Checkbox | Effect |
|---|---|
| Hide Balance Sheet | Report inaccessible + menu hidden |
| Hide Profit & Loss | Report inaccessible + menu hidden |
| Hide Partner Ledger | Report inaccessible + menu hidden |
| Hide General Ledger | Report inaccessible + menu hidden |
| Hide Trial Balance | Report inaccessible + menu hidden |
| Hide Cash Flow Statement | Report inaccessible + menu hidden |
| Hide Aged Receivable | Report inaccessible + menu hidden |
| Hide Aged Payable | Report inaccessible + menu hidden |
| Hide Tax Report | Report inaccessible + menu hidden |
| Hide Executive Summary | Report inaccessible + menu hidden |

### 📦 Inventory Restrictions
| Checkbox | Effect |
|---|---|
| Hide Scrap Menu | Scrap menu hidden; creating scrap raises error |
| Hide Physical Inventory Adjustment | Menu hidden; adjustment raises error |
| Hide Replenishment Menu | Replenishment menu hidden |
| Hide Inventory Valuation | Valuation menu hidden |
| Hide Landed Costs | Landed Costs menu hidden |

---

## Installation

1. Copy the `user_access_restrictions` folder to your Odoo **addons** directory.
2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -u user_access_restrictions -d YOUR_DB
   ```
3. Go to **Settings → Apps**, search for **"User Access & Restrictions"**, and click **Install**.

---

## Usage

1. Go to **Settings → Users & Companies → Users**.
2. Open any user.
3. Click the **"Access & Restrictions"** tab.
4. Toggle the desired checkboxes.
5. Click **Save**.
6. The affected user should refresh their browser.

---

## Security Notes

- Restrictions are enforced at **two levels**:
  1. **ORM / Python level** — even API calls respect restrictions.
  2. **JavaScript / DOM level** — fields and menu items are hidden from the UI.
- Only users in the `base.group_erp_manager` group (Odoo Administrators) can modify restriction settings.

---

## Compatibility
- Odoo **19 Community Edition**
- Depends on: `base`, `product`, `account`, `stock`, `web`
