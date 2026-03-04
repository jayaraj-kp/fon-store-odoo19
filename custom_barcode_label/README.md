# custom_barcode_label — Odoo 19 CE

## What this module does
Inherits and customises the standard **Product Barcode Label** PDF report:

| Feature | Before | After |
|---|---|---|
| Company logo | ✗ | ✅ Top-left |
| Product name | small | ✅ Large, centred |
| Barcode | with number text | ✅ Image only (number hidden) |
| Internal reference / code | shown | ✅ Removed |
| Price | small, right | ✅ Large, bottom-right |
| Paper format | default | ✅ 90 × 30 mm label |

---

## Installation

1. Copy the `custom_barcode_label` folder into your Odoo **addons path**.
2. Restart the Odoo server:
   ```
   ./odoo-bin -c odoo.conf -u custom_barcode_label
   ```
3. In Odoo → Settings → Apps → search **Custom Barcode Label** → **Install**.

---

## Usage

### Option A — From Inventory / Products list
1. Go to **Inventory → Products → Products**
2. Select one or more products (checkbox)
3. **Action → Print Labels → Product Label (Custom)**

### Option B — Assign as default label action
In **Settings → Technical → Actions → Reports**, find
`Product Label (Custom)` and set `Binding Model = product.product`.

---

## Customisation tips

### Change label size
Edit `paperformat_custom_label` in `report/product_label_report.xml`:
```xml
<field name="page_height">30</field>   <!-- mm -->
<field name="page_width">90</field>    <!-- mm -->
```

### Show/hide barcode number
In the template `custom_label_content`, the barcode number text is
intentionally omitted. To re-add it:
```xml
<span t-field="product.barcode" class="barcode-number"/>
```

### Price source
Currently uses `product.lst_price` (Sales Price).  
To use a pricelist or cost price, change `lst_price` to `standard_price`.

### Logo fallback
If the company has no logo, the company name is shown as text instead.

---

## File structure

```
custom_barcode_label/
├── __manifest__.py
├── __init__.py
└── report/
    ├── __init__.py
    └── product_label_report.xml   ← all templates, paper format, CSS
```

---

## Dependencies
- `stock`
- `product`
- No `account` module needed ✅
