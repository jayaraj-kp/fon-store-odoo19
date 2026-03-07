# custom_product_barcode
### Odoo 19 CE — Multi-Barcode & Package Quantity for POS

---

## What this module does

Adds **two extra barcode + package-quantity pairs** to every product:

| Field        | Purpose                                    | Example               |
|--------------|--------------------------------------------|-----------------------|
| Barcode      | Standard single-unit barcode (already exists) | scan 1 egg        |
| **Barcode 2**  + **Package Qty 1** | Mid-size package       | scan 1 dozen → **12 units** |
| **Barcode 3**  + **Package Qty 2** | Large/bulk package     | scan big pack → **120 units** |

When a cashier scans **Barcode 2** or **Barcode 3** in the Point of Sale,
the order line is created with the correct package quantity automatically,
so the total price is `unit_price × package_qty` — no manual entry needed.

---

## Installation

1. Copy the `custom_product_barcode/` folder into your Odoo **addons** directory.
2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u custom_product_barcode
   ```
3. In Odoo → **Settings → Apps**, search for **"Multi-Barcode"** and click **Install**.

---

## How to configure a product

1. Open **Inventory → Products → Products** (or POS → Products).
2. Open any product → **General Information** tab.
3. Scroll to the **"Package Barcodes & Quantities"** section:

   ```
   ┌──────────────────────────────────────────────────┐
   │  Barcode          [standard barcode]             │
   │                                                  │
   │  ── Package Barcodes & Quantities ──             │
   │                                                  │
   │  Package 1 (e.g. 1 Dozen = 12 units)            │
   │    Barcode 2:      [8901234567890]               │
   │    Package Qty 1:  12                            │
   │                                                  │
   │  Package 2 (e.g. 10 Dozen = 120 units)          │
   │    Barcode 3:      [8901234567891]               │
   │    Package Qty 2:  120                           │
   └──────────────────────────────────────────────────┘
   ```

4. Save the product.

---

## POS behaviour

| Scan              | Result                                              |
|-------------------|-----------------------------------------------------|
| Standard Barcode  | Adds 1 unit  → price = unit_price × 1              |
| **Barcode 2**     | Adds Package Qty 1 → price = unit_price × Qty 1   |
| **Barcode 3**     | Adds Package Qty 2 → price = unit_price × Qty 2   |

---

## Technical notes

| File | Purpose |
|------|---------|
| `models/product_template.py` | Adds `barcode2`, `barcode3`, `custom_qty1`, `custom_qty2` fields with uniqueness constraints |
| `models/pos_session.py` | Injects the new fields into the POS product data payload |
| `views/product_template_views.xml` | Adds the fields to the product form (General Information tab) |
| `static/src/js/custom_barcode.js` | Patches `PosStore` + `ProductScreen` to handle custom barcodes |

---

## Compatibility

- **Odoo 19 CE** ✅ (primary target)
- **Odoo 17 / 18 CE** ✅ (same POS architecture)
- Standard barcode field and existing POS logic are untouched.

---

## License

LGPL-3
