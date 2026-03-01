# Sale Margin / Cost Block — Odoo 19 CE

## Overview

This module blocks **order confirmation** and **invoice creation** when any sale order line's margin or cost-recovery falls below configured thresholds. It works **without the Accounting (`account`) app** — it only depends on `sale` and `stock`.

---

## Features

| Feature | Detail |
|---|---|
| **Margin % block** | Block if `(price - cost) / price * 100 < minimum` |
| **Cost Recovery % block** | Block if `price / cost * 100 < minimum` (e.g. 100 = break-even) |
| **Warn-only mode** | Post a chatter note instead of a hard block |
| **Manager override** | Users in the *Can Override Margin/Cost Block* group always bypass the hard block |
| **Live UI feedback** | Alert banner + red decoration on breaching lines |
| **Order-level totals** | Margin amount & % shown in totals section |

---

## Installation

```bash
# Copy the module into your addons path
cp -r sale_margin_block /path/to/odoo/custom_addons/

# Restart Odoo
./odoo-bin -c odoo.conf -u sale_margin_block
```

Then activate it from **Apps → search "Sale Margin Block" → Install**.

---

## Configuration

Go to **Sales → Configuration → Settings → Margin & Cost Block**.

| Setting | Description |
|---|---|
| Block by Margin % | Enable the margin guard |
| Minimum Margin % | E.g. `20` means margin must be ≥ 20 % |
| Block by Cost Recovery % | Enable the cost guard |
| Minimum Cost Recovery % | E.g. `100` means price ≥ cost; `90` allows selling 10 % below cost |
| Warn Only | Downgrade hard-block to a chatter warning for all users |

### Manager Override Group

Assign users to **Sale Margin Block / Can Override Margin/Cost Block** via:  
**Settings → Users → [user] → Other → Can Override Margin/Cost Block**

---

## How It Works

### Trigger Points

1. **`action_confirm`** — called when clicking *Confirm* on a quotation.
2. **`_create_invoices`** — called by the *Create Invoice* wizard.

### Violation Logic (per line)

```
margin_breach   = margin_enabled  AND  (price - cost) / price * 100 < margin_min
cost_breach     = cost_enabled    AND  price / cost * 100 < cost_min
```

If **any** line has a breach:
- **Hard block** → `UserError` with a list of breaching lines and their values.
- **Warn only / manager** → `message_post` chatter note; operation proceeds.

### Cost Source

`standard_price` on the product (company-specific). Multi-currency orders are handled via Odoo's built-in currency conversion at the order date.

---

## File Structure

```
sale_margin_block/
├── __init__.py
├── __manifest__.py
├── data/
│   └── res_config_defaults.xml      # Default ir.config_parameter values
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py       # Settings fields
│   ├── sale_order.py                # Validation hooks
│   └── sale_order_line.py           # Cost/margin compute fields
├── security/
│   ├── ir.model.access.csv
│   └── security_groups.xml          # Override group
└── views/
    ├── res_config_settings_views.xml
    └── sale_order_views.xml          # Columns + banner
```

---

## Extending

- To add support for purchase orders, inherit `purchase.order` / `purchase.order.line` following the same pattern in `sale_order.py`.
- To enforce thresholds on **account.move** (invoices created outside of sale), override `action_post` on `account.move` and perform the same validation.
