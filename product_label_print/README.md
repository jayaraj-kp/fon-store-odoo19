# Product Label Print Module for Odoo 19 CE
## Designed for GP-1125T Thermal Transfer Barcode Printer

---

## Label Style (matches your Image 1)

```
┌─────────────────────────────────────────┐
│ [QR] K │  KEYCHAIN 110                  │
│      C │  MRP Rs  110                   │
│      1 │                                │
│      1 │                                │
│      0 │                                │
└─────────────────────────────────────────┘
```
- QR Code top-left
- Label Code (KC110) printed **vertically** beside QR
- Product Name in **BOLD CAPS**
- MRP Rs. at bottom
- 2 labels per row (configurable)

---

## Installation

1. Copy the `product_label_print` folder to your Odoo addons path:
   ```
   /path/to/odoo/addons/product_label_print
   ```
   or your custom addons path defined in `odoo.conf`

2. Restart the Odoo service:
   ```bash
   sudo systemctl restart odoo
   # or
   sudo service odoo restart
   ```

3. In Odoo:
   - Go to **Settings > Activate Developer Mode**
   - Go to **Apps > Update App List**
   - Search for **"Product Label Print"**
   - Click **Install**

---

## Setup: Label Code Field

Each product has a new field called **Label Code** (e.g., `KC110`).

- Go to **Inventory > Products** (or **Sales > Products**)
- Open any product
- In the **General Information** tab, find **Label Code**
- Enter your code (e.g., `KC110`)
- If left empty, the **Internal Reference** is used instead

---

## Printing Labels

### Method 1: From Product Form
1. Open any product
2. Click the **🏷 Print Labels** smart button (top right)
3. Set quantity, columns, paper size
4. Click **Print Labels**

### Method 2: From Inventory Menu
1. Go to **Inventory > Operations > Print Product Labels**
2. Select products, set options
3. Click **Print Labels**

---

## Printer Setup: GP-1125T

### Paper Format Used
- Width: 150mm (2 × 75mm labels side by side)
- Height: 30mm per row
- DPI: 203
- Orientation: Portrait

### Recommended Label Stock
- **75mm × 30mm** labels (2 per row) ← matches your Image 1
- Or **50mm × 30mm** (use 1 column mode)

### Windows Driver Setup
1. Download GP-1125T driver from manufacturer
2. Set paper size to **custom: 150mm × 30mm**
3. Set print quality to **203 DPI**
4. Connect via USB or Ethernet

### Linux (CUPS) Setup
```bash
# Install CUPS
sudo apt install cups
# Add printer via http://localhost:631
# Use ZPL or generic label driver
# Set media size: 150x30mm
```

---

## Wizard Options

| Option | Description |
|--------|-------------|
| Products | Select product templates or variants |
| Number of Labels | How many copies per product |
| Columns | 1 or 2 labels per row |
| Show QR Code | Toggle QR on/off |
| Show Label Code | Toggle KC-style code on/off |
| Show MRP | Toggle price on/off |
| Label Width (mm) | Width of each label cell (default 75mm) |
| Label Height (mm) | Height of each label row (default 30mm) |

---

## Troubleshooting

### QR Code not showing
- Make sure `python-barcode` and `qrcode` are installed:
  ```bash
  pip install qrcode[pil] python-barcode --break-system-packages
  ```

### PDF looks wrong size
- Go to **Settings > Technical > Reporting > Paper Formats**
- Find **GP-1125T Label Sheet** and adjust dimensions

### Labels printing too small/large
- Adjust `label_width_mm` and `label_height_mm` in the wizard
- Also adjust your printer driver paper size to match

---

## Module Structure

```
product_label_print/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   └── product_template.py       # Adds label_code field + Print button
├── wizard/
│   ├── __init__.py
│   ├── product_label_wizard.py   # Wizard logic
│   └── product_label_wizard_views.xml
├── report/
│   ├── product_label_report.xml  # Paper format + report action
│   └── product_label_template.xml # QWeb HTML template (the label layout)
├── views/
│   └── product_views.xml         # Adds button to product form
├── security/
│   └── ir.model.access.csv
└── static/src/css/
    └── label_print.css
```
