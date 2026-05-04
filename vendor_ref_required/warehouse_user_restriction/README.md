# Warehouse User Restriction — Odoo 19 CE

## What This Module Does

Adds an **Allowed Warehouses** field to each user.
When warehouses are selected, the user is restricted to those warehouses ONLY across:

- ✅ Sales Orders
- ✅ Purchase Orders
- ✅ Inventory / Stock Pickings
- ✅ POS Sessions
- ✅ POS Orders
- ✅ Stock Quants (Inventory)

If **no warehouses are selected** → user sees everything (no restriction).

---

## Installation

1. Copy the `warehouse_user_restriction` folder into your Odoo **addons** directory
2. Restart Odoo server:
   ```
   sudo systemctl restart odoo
   ```
   or
   ```
   ./odoo-bin -c odoo.conf -u warehouse_user_restriction
   ```
3. Go to **Settings → Apps → Update App List**
4. Search for **"Warehouse User Restriction"** and click **Install**

---

## How to Use

1. Go to **Settings → Users & Companies → Users**
2. Open any user
3. Click the **Access Rights** tab
4. Under the **Inventory** section, you'll see **Allowed Warehouses**
5. Add the warehouses this user is allowed to work with
6. Save

---

## Important Notes

- **Admin users (superuser)** bypass all record rules by default in Odoo — restriction applies to regular users only
- After installing, **clear browser cache** and re-login to see changes
- If you add/remove warehouses for a user, changes take effect immediately on next page load

---

## Troubleshooting

**Field not showing on user form?**
→ Make sure the module is installed and you upgraded the view. Try Settings → Activate Developer Mode → Settings → Technical → Views → search `res.users.form.warehouse.restriction` and check it exists.

**Restriction not working?**
→ Check Settings → Technical → Record Rules → search "Allowed Warehouses" — all rules should be listed there.
