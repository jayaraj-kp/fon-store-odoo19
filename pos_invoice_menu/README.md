# POS Invoice Menu — Odoo 19 CE Custom Module

Adds an **Invoices** button to the POS top bar that shows all completed
orders for the current session, with order line drill-down. Works **without**
the core `account` (accounting) module.

---

## Features

- ✅ "Invoices" button injected into the POS top bar
- ✅ Displays all paid/done orders for the active session
- ✅ Real-time search by order ref or customer name
- ✅ Summary bar: total orders + total amount
- ✅ Click any row to expand and see order lines
- ✅ Refresh button to reload data
- ✅ Works without accounting module

---

## Installation

1. Copy `pos_invoice_menu/` into your Odoo custom addons directory:
   ```
   /path/to/odoo/custom_addons/pos_invoice_menu/
   ```

2. Make sure the path is in `addons_path` inside your `odoo.conf`:
   ```ini
   addons_path = /path/to/odoo/addons,/path/to/odoo/custom_addons
   ```

3. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf
   ```

4. In Odoo backend:  
   **Apps → Update Apps List → Search "POS Invoice Menu" → Install**

5. Open a POS session and look for the **Invoices** button in the top bar.

---

## XPath Troubleshooting

### Error: `Element cannot be located in element tree`

This means the XPath target class doesn't exist in your POS build.

**Step 1:** Open POS → browser DevTools (F12) → Console tab, paste:
```javascript
// Run this in the POS browser console to find the top bar class
document.querySelector('.pos-top-bar') && console.log('✅ pos-top-bar found')
document.querySelector('.pos-top-bar-buttons') && console.log('✅ pos-top-bar-buttons found')
document.querySelector('.menus-buttons') && console.log('✅ menus-buttons found')
document.querySelector('.top-content') && console.log('✅ top-content found')
```

**Step 2:** Edit `static/src/xml/InvoiceButton.xml` and replace the XPath with the one that was found:

| If this class exists | Use this XPath |
|---|---|
| `pos-top-bar-buttons` | `//div[hasclass('pos-top-bar-buttons')]` |
| `pos-top-bar` | `//div[hasclass('pos-top-bar')]` |
| `menus-buttons` | `//div[hasclass('menus-buttons')]` |
| `top-content` | `//div[hasclass('top-content')]` |

**Step 3:** Upgrade the module and clear browser cache:
```bash
# Upgrade module
python odoo-bin -c odoo.conf -u pos_invoice_menu

# Then in browser: Ctrl+Shift+R (hard refresh)
```


---

## File Structure

```
pos_invoice_menu/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── pos_order.py          ← Python: exposes session orders via ORM
└── static/src/
    ├── js/
    │   ├── InvoiceButton.js   ← OWL: top bar button component
    │   └── InvoiceListScreen.js ← OWL: full invoice screen
    ├── xml/
    │   ├── InvoiceButton.xml  ← Template + ProductScreen patch
    │   └── InvoiceListScreen.xml ← Invoice screen template
    └── css/
        └── pos_invoice.css   ← Styles
```

---

## Compatibility

| Field       | Value           |
|-------------|-----------------|
| Odoo        | 19.0 CE         |
| POS         | Requires `point_of_sale` |
| Accounting  | NOT required    |
| JS Framework| OWL (Odoo Web Library) |
| License     | LGPL-3          |
