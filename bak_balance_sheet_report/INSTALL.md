# BAK Balance Sheet Inline Report — Installation Guide

## Step 1 — Copy module
Place `bak_balance_sheet_report/` in your Odoo addons path:
```
/opt/odoo19/custom_addons/bak_balance_sheet_report/
```

## Step 2 — Restart Odoo
```bash
sudo systemctl restart odoo
```

## Step 3 — Install the module
Go to Apps → Update App List → search "Balance Sheet Inline" → Install

---

## ⚠️ If you get a menu parent error

The menu parent ID depends on your exact version of `base_accounting_kit`.
Run this SQL query in your Odoo shell or via psql to find the correct ID:

```sql
SELECT module || '.' || name AS xmlid, name
FROM ir_model_data
WHERE model = 'ir.ui.menu'
  AND module LIKE '%account%'
  AND name LIKE '%report%'
ORDER BY module, name;
```

Or in an Odoo shell (`odoo shell`):
```python
menus = env['ir.model.data'].search([
    ('model', '=', 'ir.ui.menu'),
    ('name', 'ilike', 'report'),
])
for m in menus:
    print(m.module + '.' + m.name)
```

Then open `views/menu_views.xml` and replace:
```xml
parent="base_accounting_kit.menu_accounting_reports"
```
with the correct XML ID you found above.

---

## Optional: XLSX Export
Install xlsxwriter on your server:
```bash
pip3 install xlsxwriter
```

## Optional: PDF Export
Requires wkhtmltopdf (standard Odoo requirement, usually already installed).
