# Customer Gender (Male/Female) — Odoo 19 CE

Adds a **Gender** field (Male / Female) to Contacts/Customers (`res.partner`)
and lets you filter or group customers by gender — no Accounting app required.

## What it adds
- A `gender` Selection field (Male / Female) on the Contact form.
- An optional "Gender" column on the Contacts list view.
- Search **Filters**: "Male", "Female".
- **Group By**: "Gender".

## Installation
1. Copy the `partner_gender` folder into your Odoo `addons` (custom addons) path,
   e.g. `/opt/odoo/custom-addons/partner_gender` (or wherever your
   `addons_path` in `odoo.conf` points).
2. Restart the Odoo service.
3. Go to **Apps** → click **Update Apps List** (enable Developer Mode first if
   the option isn't visible: Settings → General Settings → scroll down →
   Activate Developer Mode, or add `?debug=1` to the URL).
4. Search for **"Customer Gender"** and click **Install**.

## Usage
1. Open **Contacts** app (or Customers under Sales).
2. Open any contact/customer form — you'll see the new **Gender** field
   (near the Phone field). Set it to Male or Female and Save.
3. In the Contacts list view, go to the search bar:
   - Type/click **Filters** → choose **Male** or **Female** to filter.
   - Click **Group By** → choose **Gender** to group customers by gender.
   - You can also type "Male" or "Female" directly in the search box.

## Notes
- This module only depends on `base` and `contacts` — it does NOT require
  the Accounting app.
- If, after installing, the "Male"/"Female" filters or "Gender" group-by
  don't appear (can happen if Odoo's core search view structure differs
  slightly in your build), you can always still filter manually by typing
  `Gender` in the search bar and selecting the value, since the field itself
  is always added to the search view.
- To uninstall: Apps → search "Customer Gender" → Uninstall. This will also
  remove the `gender` field and its stored data.

## Folder structure
```
partner_gender/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── res_partner.py
└── views/
    └── res_partner_views.xml
```
