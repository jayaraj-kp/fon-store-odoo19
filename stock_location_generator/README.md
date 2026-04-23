# Stock Location Generator (Odoo 19 CE)

A lightweight custom module that adds a **"Generate Locations"** wizard to Odoo's
Inventory → Configuration → Locations list view — matching the dialog shown in the
Odoo interface screenshot.

---

## Features

| Feature | Details |
|---|---|
| **Rack generation** | Creates numbered internal locations (e.g. *Rack 1 … Rack 10*) |
| **Box generation** | Creates Box sub-locations inside an existing Rack |
| **Custom prefix** | Optional prefix (e.g. `R-` → R-1, R-2 …). Defaults to `Rack ` / `Box ` |
| **Range selector** | From / To integer range |
| **Warehouse selector** | Auto-fills parent location (Stock) from the chosen warehouse |
| **Duplicate safety** | Skips locations that already exist; reports skipped names |
| **Access control** | Managers can create/delete; regular stock users can create |

---

## Installation

1. Copy the `stock_location_generator` folder into your Odoo **addons** path.
2. Restart the Odoo service.
3. Go to **Apps**, search `Stock Location Generator`, and click **Install**.

---

## Usage

1. Navigate to **Inventory → Configuration → Locations**.
2. Select one or more locations in the list view (or none — the action is always available in the Action menu ⚙).
3. Click **Action ⚙ → Generate Locations**.
4. Fill in the wizard:
   - **Create**: choose *Rack* or *Box*
   - **Prefix**: optional (leave blank for default labels)
   - **From / To**: numeric range
   - **Warehouse**: pick the warehouse
   - **In**: parent location (auto-filled from warehouse)
5. Click **Generate**.

---

## File Structure

```
stock_location_generator/
├── __init__.py
├── __manifest__.py
├── security/
│   └── ir.model.access.csv
├── views/
│   └── stock_location_views.xml
└── wizard/
    ├── __init__.py
    ├── stock_location_generate_wizard.py
    └── stock_location_generate_wizard_views.xml
```
