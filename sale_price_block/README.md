# sale_price_block — Block Sale Below Cost Price

## Overview
This Odoo 19 CE module **blocks sale order confirmation** when any order line
has a unit price lower than the product's cost price (`standard_price`).

## Behavior
- ✅ Sales person can freely enter any price on the order lines (no warning on input).
- ❌ When the **Confirm** button is clicked, if any product's unit price < cost price,
  an error dialog is shown with a detailed list of the offending products.
- The order **cannot be confirmed** until the prices are corrected.

## Error Message Example
```
Cannot confirm sale order "S00042".

The following product(s) have a unit price BELOW their cost price:

  • Laptop Pro  →  Sale Price: $ 500.00  |  Cost Price: $ 750.00
  • USB Hub     →  Sale Price: $ 5.00    |  Cost Price: $ 8.00

Please update the sale prices before confirming the order.
```

## Settings
Go to **Sales → Configuration → Settings** and look for:
> **Block Sale Below Cost Price** (toggle ON/OFF)

When disabled, the check is skipped and orders confirm normally.

## Installation
1. Copy the `sale_price_block` folder into your Odoo addons directory.
2. Restart the Odoo server.
3. Go to **Apps → Update App List**.
4. Search for `Block Sale Below Cost` and click **Install**.

## Technical Details
| Item | Value |
|------|-------|
| Odoo Version | 19.0 CE |
| Module Name | `sale_price_block` |
| Depends | `sale_management` |
| Config Parameter | `sale_price_block.block_below_cost` |

## Files
```
sale_price_block/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── sale_order.py          ← Core logic (confirm block)
│   └── res_config_settings.py ← Settings toggle
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv
└── README.md
```
