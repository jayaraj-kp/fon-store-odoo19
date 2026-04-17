# Custom Cost: Total Value ÷ Latest Purchase Price
### Odoo 19 Community Edition — Custom Module

---

## What This Module Does

Automatically updates a product's **Cost (Standard Price)** after every
purchase receipt or vendor bill using this formula:

```
New Cost = Total Stock Value ÷ Latest Purchase Unit Price
```

### Example

| Step | Action | Qty | Price | Stock Value |
|------|--------|-----|-------|-------------|
| 1 | Purchase | +100 | ₹200 | ₹20,000 |
| 2 | Sale | -50 | — | ₹10,000 (50 × ₹200) |
| 3 | Purchase | +100 | ₹250 | ₹35,000 (₹10,000 + ₹25,000) |
| ✅ | **New Cost** | — | — | **₹35,000 ÷ ₹250 = ₹140** |

---

## Installation

1. Copy the `custom_avco_cost` folder into your Odoo addons directory:
   ```
   /path/to/odoo/custom_addons/custom_avco_cost/
   ```

2. Restart Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u custom_avco_cost
   ```

3. Go to **Settings → Apps**, enable developer mode, search for
   **"Custom Cost"** and click **Install**.

---

## How to Enable Per Product

1. Go to **Inventory → Products → Products**
2. Open the product (e.g., AVCO NON 2)
3. In **General Information** tab, find the **Cost** field
4. Below it, toggle ON: **"Custom Cost (Value ÷ Latest PO Price)"**
5. Save

Now every time you validate a purchase receipt for this product,
the cost field updates automatically.

---

## When Does It Trigger?

| Event | Triggers Recompute? |
|-------|-------------------|
| Purchase Receipt Validated (`button_validate`) | ✅ Yes |
| Stock Move Done (`_action_done`) | ✅ Yes (safety net) |
| Vendor Bill Confirmed (`action_post`) | ✅ Yes (for Periodic valuation) |
| Sales Order / Delivery | ❌ No |
| Manual stock adjustment | ❌ No |
| Click "Recompute Custom Cost" button | ✅ Yes (manual) |

---

## Works With Both Valuation Types

- **Periodic (at closing)** — value = `qty_on_hand × standard_price`
- **Perpetual (at invoicing)** — value = sum of `stock.valuation.layer`

---

## Formula Details

```
After Purchase 2:
  Old remaining stock value  = 50 qty × ₹200          = ₹10,000
  New purchase value         = 100 qty × ₹250          = ₹25,000
  ─────────────────────────────────────────────────────────────
  Total Stock Value                                    = ₹35,000
  Latest Purchase Price                                =    ₹250
  ─────────────────────────────────────────────────────────────
  New Product Cost           = ₹35,000 ÷ ₹250          =   ₹140
```

Old stock is **NOT re-valued** — its original cost is preserved.
Only the `standard_price` (cost field) changes to reflect the new formula.

---

## Files

```
custom_avco_cost/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── product_product.py    ← Core formula logic
│   └── stock_move.py         ← Triggers on purchase events
├── security/
│   └── ir.model.access.csv
├── views/
│   └── product_views.xml     ← Toggle + manual button in product form
└── README.md
```
