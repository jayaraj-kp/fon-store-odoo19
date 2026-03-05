# POS Cash Customer Module

## Purpose
All customers created from the POS "Create" button are automatically saved
as **contacts under a single CASH CUSTOMER partner** instead of as standalone partners.

---

## Installation Steps

1. Copy the `pos_cash_customer` folder into your Odoo **addons** directory.
2. Restart the Odoo server.
3. In Odoo backend → **Apps** → search `pos_cash_customer` → **Install**.

---

## Setup (One-time)

### Step 1: Create the CASH CUSTOMER partner
Go to **Contacts** → **New**:
- Name: `CASH CUSTOMER`
- Type: Person (or Company, your choice)
- Save it.

### Step 2: Configure the module
Go to **Point of Sale** → **Configuration** → **Settings**:
- Find the **"Cash Customer Partner"** field (in the Connected Devices section).
- Select the `CASH CUSTOMER` partner you just created.
- **Save**.

---

## How It Works After Setup

| Scenario | What Happens |
|----------|-------------|
| Click **Create** in POS customer screen | Opens "Create Contact" form with parent = CASH CUSTOMER |
| Save the contact | New customer appears under CASH CUSTOMER in Contacts |
| No cash_customer_id configured | Falls back to standard Odoo POS customer creation |

---

## Odoo Version
- **Odoo 19 Community Edition**
- Requires: `point_of_sale` module
- Does NOT require accounting module

---

## Notes
- The `CASH CUSTOMER` partner itself is never selected as the customer on orders.
- Each individual contact (e.g., "John", "Mary") is selected on orders.
- If you want truly anonymous cash sales, you can also just select `CASH CUSTOMER` directly from the customer list without creating a new contact.
