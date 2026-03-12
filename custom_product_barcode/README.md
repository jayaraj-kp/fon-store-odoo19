# custom_product_barcode
### Odoo 19 CE — Multi-Barcode, Package Quantity & Combo Limit for POS

---

## What this module does

Adds **two extra barcode + package-quantity pairs** with an optional **per-bill combo limit** to every product:

| Field                | Purpose                                        | Example                          |
|----------------------|------------------------------------------------|----------------------------------|
| Barcode              | Standard single-unit barcode (already exists) | scan 1 egg                       |
| **Barcode 2** + **Package Qty 1** + **Max Combo Qty 1** | Mid-size package with limit | scan 1 dozen → **12 units**, max **5** per bill |
| **Barcode 3** + **Package Qty 2** + **Max Combo Qty 2** | Large/bulk package with limit | scan big pack → **120 units**, max **2** per bill |

When a cashier scans **Barcode 2** or **Barcode 3** in the Point of Sale:
- The order line is created with the correct package quantity and price automatically.
- If **Max Combo Qty** is set (> 0), scanning is **blocked** once that limit is reached for the current bill.
- A notification shows remaining scans allowed. When the limit is hit, a red ⛔ warning is shown.

---

## Installation

1. Copy the `custom_product_barcode/` folder into your Odoo **addons** directory.
2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u custom_product_barcode
   ```
3. In Odoo → **Settings → Apps**, search for **"Multi-Barcode"** and click **Install** (or **Upgrade** if already installed).

---

## How to configure a product

1. Open **Inventory → Products → Products** (or POS → Products).
2. Open any product → **General Information** tab.
3. Scroll to the **"Package Barcodes, Quantities & Combo Limits"** section:

   ```
   ┌──────────────────────────────────────────────────────────┐
   │  Barcode          [standard barcode]                     │
   │                                                          │
   │  ── Package Barcodes, Quantities & Combo Limits ──       │
   │                                                          │
   │  Package 1 (e.g. 1 Dozen = 12 units)                    │
   │    Barcode 2:        [8901234567890]                     │
   │    Package Qty 1:    12                                  │
   │    Package Price 1:  ₹150.00  (0 = unit price × qty)    │
   │    Max Combo Qty 1:  5        (0 = unlimited)            │
   │                                                          │
   │  Package 2 (e.g. 10 Dozen = 120 units)                  │
   │    Barcode 3:        [8901234567891]                     │
   │    Package Qty 2:    120                                 │
   │    Package Price 2:  ₹1200.00                           │
   │    Max Combo Qty 2:  2        (0 = unlimited)            │
   └──────────────────────────────────────────────────────────┘
   ```

4. Save the product.

---

## POS behaviour

| Scan              | Result                                                                     |
|-------------------|----------------------------------------------------------------------------|
| Standard Barcode  | Adds 1 unit → price = unit_price × 1 (no limit)                          |
| **Barcode 2**     | Adds Package Qty 1 → price = Package Price 1 (or unit price × qty)       |
| **Barcode 2** (over limit) | ⛔ Blocked — shows "limit reached" notification, nothing added  |
| **Barcode 3**     | Adds Package Qty 2 → price = Package Price 2 (or unit price × qty)       |
| **Barcode 3** (over limit) | ⛔ Blocked — shows "limit reached" notification, nothing added  |

> **Limit resets on each new bill.** Starting a new order gives a fresh count.

---

## Max Combo Qty examples

| Max Combo Qty | Behaviour                                                    |
|:---:|--------------------------------------------------------------|
| `0` | Unlimited — no restriction, scan as many times as needed     |
| `5` | Barcode can be scanned up to 5 times per bill; 6th scan is blocked |
| `1` | Only 1 scan per bill allowed                                 |

---

## Technical notes

| File | Purpose |
|------|---------|
| `models/product_template.py` | Adds `barcode2`, `barcode3`, `custom_qty1/2`, `custom_price1/2`, **`max_combo_qty1/2`** fields |
| `models/product_product.py` | Related fields on `product.product` (for POS payload) |
| `models/pos_session.py` | Injects all custom fields into the POS product data payload |
| `controllers/custom_barcode.py` | REST endpoint returning barcode map including `max_combo_qty` |
| `views/product_template_views.xml` | Adds all fields to the product form |
| `static/src/js/custom_barcode.js` | Patches `ProductScreen`; enforces combo limit in-browser per bill |

---

## Compatibility

- **Odoo 19 CE** ✅ (primary target)
- **Odoo 17 / 18 CE** ✅ (same POS architecture)
- Standard barcode field and existing POS logic are untouched.

---

## License

LGPL-3
