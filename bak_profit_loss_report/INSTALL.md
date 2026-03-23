# BAK Profit & Loss Inline Report — Installation Guide

## Step 1 — Copy module
Place `bak_profit_loss_report/` in your Odoo addons path:
```
/opt/odoo19/custom_addons/bak_profit_loss_report/
```

## Step 2 — Restart Odoo
```bash
sudo systemctl restart odoo
```

## Step 3 — Install the module
Go to **Apps → Update App List** → search **"Profit & Loss Inline"** → Install

---

## ⚠️ If you get a menu parent error

Run this in psql to find the correct reporting menu ID:
```sql
SELECT module || '.' || name AS xmlid
FROM ir_model_data
WHERE model = 'ir.ui.menu'
  AND module LIKE '%account%'
  AND name LIKE '%report%'
ORDER BY module, name;
```

Then open `views/menu_views.xml` and replace:
```xml
parent="base_accounting_kit.menu_accounting_reports"
```
with the correct XML ID you found above.

---

## Report Structure

| Section              | Account Types Included                            |
|----------------------|---------------------------------------------------|
| Revenue              | `income`, `income_other`                          |
| Cost of Revenue      | `expense_direct_cost`                             |
| **Gross Profit**     | Revenue − Cost of Revenue                         |
| Operating Expenses   | `expense`, `expense_depreciation`                 |
| **Net Profit**       | Gross Profit − Operating Expenses                 |

---

## Optional: XLSX Export
```bash
pip3 install xlsxwriter
```

## Optional: PDF Export
Requires wkhtmltopdf (standard Odoo requirement).

---

## Debug
Visit `/bak/profit_loss/debug_schema` to inspect your DB column structure.
