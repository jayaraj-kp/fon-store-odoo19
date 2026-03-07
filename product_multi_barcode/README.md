# Product Multi-Barcode & Packaging Module
### For Odoo 17 / 18 / 19 Community Edition

---

## What this module does

| Slot | Field | Qty Field | Label Field | Use-case |
|------|-------|-----------|-------------|----------|
| 1 | `barcode` (built-in) | 1 unit | Product name | Single unit |
| 2 | `barcode_2` | `package_qty_2` | `package_name_2` | e.g. 1 Dozen = 12 |
| 3 | `barcode_3` | `package_qty_3` | `package_name_3` | e.g. Big Carton = 120 |

When you scan **Barcode 2** in POS, the order line is created with **qty = package_qty_2** (e.g. 12) and the price = `unit_price × 12`.

---

## Installation

1. Copy the `product_multi_barcode` folder into your Odoo **addons** directory:
   ```
   /your-odoo-path/custom_addons/product_multi_barcode/
   ```

2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u product_multi_barcode
   ```

3. Activate **Developer Mode** in Odoo:
   - Settings → General Settings → scroll to "Developer Tools" → Activate

4. Go to **Apps** → update apps list → search for **"Product Multi Barcode"** → Install.

---

## How to configure a product

1. Open **Inventory → Products → Products** (or any product form).
2. In **General Information** tab, scroll down to the new section  
   **"Additional Barcodes & Packaging"**.

### Example – Rice 1 kg

| Field | Value |
|-------|-------|
| Barcode (built-in) | `8901234560001` |
| **Barcode 2** | `8901234560002` |
| **Package Qty 2** | `12` |
| **Package Label 2** | `Dozen (12 kg)` |
| **Barcode 3** | `8901234560003` |
| **Package Qty 3** | `120` |
| **Package Label 3** | `Big Carton (120 kg)` |

---

## How scanning works in POS

| Scanned barcode | Qty added to order | Price charged |
|----------------|-------------------|---------------|
| `8901234560001` | 1 | ₹ 50 |
| `8901234560002` | 12 | ₹ 600 |
| `8901234560003` | 120 | ₹ 6,000 |

---

## How scanning works in Sales Orders

Use the server-side method from code or a custom button:

```python
self.env['sale.order'].add_product_by_barcode(order_id, '8901234560002')
# → adds 12 units of Rice 1 kg to the sale order
```

---

## File structure

```
product_multi_barcode/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── product_template.py   ← new fields + constraint + barcode resolver
│   ├── product_product.py    ← variant-level resolver
│   ├── pos_order.py          ← sends fields to POS front-end
│   └── sale_order_line.py    ← sale order barcode helper
├── views/
│   ├── product_template_views.xml  ← UI changes (General Info + Barcode tab)
│   ├── product_product_views.xml
│   └── assets.xml                  ← loads the POS JS patch
├── static/src/js/
│   └── multi_barcode_pos.js        ← POS barcode scanning patch
└── security/
    └── ir.model.access.csv
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Fields not visible | Make sure you are in the product **Template** form (not variant) |
| POS not scanning pack barcodes | Close & reopen the POS session after installing the module |
| Duplicate barcode error | Each barcode must be globally unique across all 3 slots |
| Module not found | Check the addons path in `odoo.conf` includes your custom_addons folder |

---

## Odoo version compatibility

Tested on **Odoo 17 CE**. The same code works on 18 and 19 CE with no changes.  
For Odoo 16 CE, change the `version` in `__manifest__.py` to `16.0.1.0.0`.
