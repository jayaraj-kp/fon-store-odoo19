# Custom Product Label 50×25mm — Odoo 19 CE Module

## Features
- **Label size**: 50mm × 25mm thermal roll
- **Left side**: Company logo (B&W, vertical)
- **Top center**: Item name (Arial Narrow font, 2 lines)
- **Top right**: MRP with price (₹)
- **Bottom left**: Instagram QR code
- **Bottom center**: Barcode (no barcode number text)
- No product code shown

---

## Installation

### 1. Install Python dependencies
```bash
pip install python-barcode[images] qrcode[pil]
```

### 2. Copy module to Odoo addons
```bash
cp -r custom_product_label /path/to/your/odoo/custom_addons/
```

### 3. Enable developer mode in Odoo
Settings → Activate Developer Mode

### 4. Update Apps List
Settings → Apps → Update Apps List

### 5. Install the module
Search for **"Custom Product Label 50x25mm"** and click Install.

---

## Configuration

### Company Instagram Handle (global default)
Settings → Companies → Your Company → **Instagram Handle**
Enter your Instagram handle, e.g. `@yourshop` or `https://instagram.com/yourshop`

### Per-Product Instagram Override
Inventory/Product → Product Form → **Instagram Handle**
Leave blank to use the company default.

---

## Printing Labels

### From Product List:
1. Go to **Inventory → Products → Products**
2. Select one or more products (checkbox)
3. Click **Action → Print → Custom Product Label 50x25**

### From Product Form:
1. Open a product
2. Click **Print → Custom Product Label 50x25**

---

## Printer Setup (Recommended)
- Use a **thermal label printer** (e.g. Zebra, Xprinter, TSC)
- Set paper size to **50mm × 25mm**
- Set DPI to **203 dpi** or **300 dpi**
- In your browser print dialog: set paper size to custom 50×25mm, margins = 0

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No barcode shown | Ensure product has a barcode set |
| No QR code | Set Instagram handle in company or product |
| Logo not B&W | Module applies CSS grayscale filter |
| Barcode library error | `pip install python-barcode[images]` |
| QR library error | `pip install qrcode[pil]` |

---

## File Structure
```
custom_product_label/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── product_label.py        ← barcode/QR generation, helper fields
├── report/
│   └── report_product_label.xml ← QWeb template + paper format
├── views/
│   └── product_label_action.xml ← Form fields, actions
└── static/src/scss/
    └── label_style.scss         ← Label CSS/SCSS styles
```
