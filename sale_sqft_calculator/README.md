# Sale Square Feet Calculator — Odoo 19 CE

## Overview
This module adds a Square Feet Calculator popup to Sale Order lines.
Select a product, click the 📐 button, enter Width and Height — the quantity
is automatically updated with the calculated square footage.

## Features
- 📐 Calculator button on every sale order line
- Popup dialog with Width × Height input
- Live sq.ft calculation preview
- Auto-updates the line quantity on Apply
- Width / Height / Sq.Ft columns (toggleable) on order lines

## Installation
1. Copy `sale_sqft_calculator/` into your Odoo custom addons path
2. Restart Odoo server
3. Go to **Settings → Apps → Update Apps List**
4. Search for **"Sale Square Feet Calculator"** and click **Install**

## Usage
1. Open any Sale Order
2. Add a product to the order lines
3. Click the **📐** button on that line
4. Enter **Width (ft)** and **Height (ft)** in the popup
5. The result shows as **sq.ft**
6. Click **✔ Apply to Order Line** — the Quantity is updated automatically

## Notes
- Default unit is **feet**. To use inches, change `_compute_sqft` in
  `sqft_wizard.py` to divide by 144: `area = (width * height) / 144`
- Compatible with Odoo 19 Community Edition
- Author: TJ Ardor Creations
