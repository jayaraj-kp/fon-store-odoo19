# POS Special Offers Module
### Odoo 19 Community Edition

---

## 📦 Installation

1. **Copy the module** folder `pos_special_offers` into your Odoo addons directory:
   ```
   /your-odoo-path/addons/pos_special_offers/
   ```

2. **Restart the Odoo server**:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u pos_special_offers
   ```

3. **Activate Developer Mode** in Odoo:
   - Go to Settings → General Settings → scroll to bottom → Activate Developer Mode

4. **Install the module**:
   - Go to Apps → search for **"POS Special Offers"** → click Install

---

## 🚀 How to Use

### In the POS Interface

1. Open your POS session
2. In the **top menu bar**, you will see a red **🎁 Offers** button
3. Click it to open the Special Offers dialog

### Creating an Offer

In the **"Create Offer"** tab:

| Field | Description |
|-------|-------------|
| Offer Name | Give the offer a name (e.g. "Weekend Sale") |
| Select Products | Pick one or more products (hold Ctrl to multi-select) |
| Select Category | Optionally select a POS category to apply to all its products |
| From Date | Start date of the offer |
| To Date | End date of the offer |
| Active From Time | Time of day when offer becomes active (e.g. 00:00) |
| Active Until Time | Time of day when offer expires (e.g. 23:59) |
| Discount Type | Choose Percentage (%) or Fixed Price |
| Discount Value | Enter the discount amount |

Click **✅ Create Offer** — the offer is saved and will be automatically applied to selected products when they are added to orders during the valid date/time window.

### Viewing Active Offers

Click the **"Active Offers"** tab in the dialog to see all currently running offers.

---

## 🛠️ Backend Management

Managers can also manage offers from the Odoo backend:

- Navigate to: **Point of Sale → Special Offers**
- Create, edit, activate/deactivate offers
- List view shows color-coded status:
  - 🟢 Green = Currently Active
  - 🔵 Blue = Upcoming
  - Grey = Expired

---

## ⚙️ How Discounts Are Applied

When a product is added to a POS order:
1. The system checks all active offers for the current date & time
2. If the product (or its category) matches an offer, the discount is applied:
   - **Percentage**: Price reduced by X%
   - **Fixed Price**: Product sells at the fixed price

---

## 📁 Module Structure

```
pos_special_offers/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── pos_special_offer.py        # Offer data model
├── views/
│   └── pos_special_offer_views.xml # Backend views & menus
├── security/
│   └── ir.model.access.csv         # Access rights
└── static/src/
    ├── css/
    │   └── special_offer.css       # Popup styling
    ├── js/
    │   ├── SpecialOfferButton.js   # Top bar button component
    │   └── SpecialOfferPopup.js    # Popup dialog component
    └── xml/
        └── special_offer.xml       # OWL templates
```

---

## 🔐 Access Rights

| Role | Read | Create | Edit | Delete |
|------|------|--------|------|--------|
| POS Manager | ✅ | ✅ | ✅ | ✅ |
| POS User (Cashier) | ✅ | ✅ | ❌ | ❌ |

---

## 💡 Notes

- Offers with overlapping products: the **first matching** offer is applied
- Category offers apply to **all products** belonging to that POS category
- Offers outside their date/time window are automatically ignored
- This module is compatible with **Odoo 19 Community Edition**
