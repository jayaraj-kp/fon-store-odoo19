# sale_cost_price_block — Odoo 19 CE Custom Module

## Purpose
Blocks sales orders and POS orders from being confirmed/paid when any product
line is priced **below the product's cost price** (`standard_price`).

---

## Features

| Feature | Details |
|---|---|
| Sales Order Block | Raises error on **Confirm** if any line is below cost |
| Real-time Validation | ValidationError when **saving** a below-cost line |
| POS Block | Blocks **Validate Payment** if any line is below cost |
| POS Warning | Instant popup warning when price is entered below cost |
| Manager Override | Optionally let Sales Managers bypass the check |
| Per-company Config | Enabled/disabled from Settings |

---

## Installation

1. Copy the `sale_cost_price_block` folder into your Odoo `addons` directory:
   ```
   /your_odoo_path/addons/sale_cost_price_block/
   ```

2. Restart the Odoo service:
   ```bash
   sudo systemctl restart odoo
   # or
   ./odoo-bin -c odoo.conf -u sale_cost_price_block
   ```

3. In Odoo, go to **Apps** → Update Apps List → Search for  
   **"Block Sale Below Cost Price"** → Install.

---

## Configuration

1. Go to **Settings → Sales** (or search "Cost Price Protection").
2. Enable **Block Sales Below Cost Price**.
3. Optionally enable **Allow Sales Manager Override** so managers can confirm
   orders even with below-cost lines.

---

## How It Works

### Sales Module
- When a salesperson sets a unit price below `product.standard_price`, a
  `ValidationError` fires immediately on save.
- On clicking **Confirm Order**, an additional `UserError` lists all violations.
- If Manager Override is on, `sales_team.group_sale_manager` users bypass both checks.

### POS Module
- `standard_price` is loaded into POS product data at session start.
- When a cashier enters a price below cost, a **warning popup** appears immediately.
- When clicking **Validate Payment**, if any line is still below cost, payment
  is **blocked** with a clear message.
- Server-side: `pos.order._order_fields()` performs a final validation before
  the order is saved to the database.

---

## File Structure

```
sale_cost_price_block/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py   ← Settings toggle
│   ├── sale_order.py            ← Sales order / line validation
│   └── pos_order.py             ← POS order validation + data injection
├── views/
│   └── res_config_settings_views.xml
├── security/
│   └── ir.model.access.csv
└── static/src/
    ├── js/
    │   └── cost_price_check.js  ← POS frontend patches
    └── xml/
        └── cost_price_warning.xml
```

---

## Notes

- **Cost price** used is `product.standard_price` (the "Cost" field on the product form).
- Currency conversion is applied automatically when the sale order currency differs
  from the company currency.
- POS uses company currency (no conversion); ensure product cost prices are in
  your company's currency.
- Works with Odoo **19 Community Edition**.
