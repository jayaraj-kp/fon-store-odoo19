# Stock Internal Transfer Journal Entry

**Odoo Version**: 19.0 Community Edition  
**Module Technical Name**: `internal_journal_entry`  
**Category**: Inventory  

---

## What This Module Does

Whenever an **Internal Stock Transfer** is validated (state → `done`) — whether done **manually** or triggered via **Auto Replenishment** — this module automatically creates and posts a double-sided journal entry:

```
Stock Transfer A/C    DR   (product cost × qty done)
Stock Transfer A/C    CR   (same amount)
```

Both lines use the **same configurable account**, giving a clean audit trail of every internal movement without affecting the net balance of that account.

---

## Module Structure

```
internal_journal_entry/
├── __init__.py
├── __manifest__.py
├── hooks.py                          ← post_init_hook (auto-setup)
├── data/
│   └── account_data.xml              ← Default journal + account on install
├── models/
│   ├── __init__.py
│   ├── res_config_settings.py        ← Company fields + settings model
│   └── stock_picking.py              ← Core JE creation logic
├── security/
│   └── ir.model.access.csv           ← Access rights
└── views/
    ├── res_config_settings_views.xml ← Settings page section
    └── stock_picking_views.xml       ← Smart button + tab on picking form
```

---

## Dependencies

| Module  | Reason |
|---------|--------|
| `stock` | Stock picking, move lines, replenishment |
| `account` | `account.move`, `account.journal`, `account.account` |

> ⚠️ The `account` module (Odoo CE Invoicing) **must be installed**.  
> This module does NOT require Odoo Enterprise Accounting.

---

## Installation

1. Copy the `internal_journal_entry` folder into your Odoo **addons path**.
2. Restart the Odoo server:
   ```bash
   ./odoo-bin -c odoo.conf --stop-after-init
   ./odoo-bin -c odoo.conf
   ```
3. Go to **Apps** → Search `internal_journal_entry` → **Install**.
4. On install, a default **Stock Transfer Journal** (`SITJ`) and  
   **Stock Transfer Account** (`199900`) are created automatically.

---

## Configuration

After installation:

1. Go to **Inventory → Configuration → Settings**
2. Scroll to the **Internal Transfer Journal Entry** section
3. Select:
   - **Stock Transfer Journal** → any General/Miscellaneous journal
   - **Stock Transfer Account** → the account for DR & CR lines
4. Click **Save**

> 💡 The defaults created on install work immediately. You can change them anytime.

---

## How It Works — Step by Step

### Manual Internal Transfer

```
Inventory → Operations → Transfers
→ Create Transfer (type = Internal)
→ Fill products + quantities
→ Click [Validate]
      │
      └─► _action_done() fires
              └─► _is_internal_transfer() → True
                      └─► _create_internal_transfer_journal_entry()
                              ├─ Reads journal & account from company config
                              ├─ Computes amount = Σ(qty_done × standard_price)
                              ├─ Creates account.move (type = entry)
                              │     Line 1: Stock Transfer A/C  DR  amount
                              │     Line 2: Stock Transfer A/C  CR  amount
                              └─ Posts the entry (action_post)
```

### Auto Replenishment

```
Inventory → Operations → Replenishment
→ Set route = "Resupply from" another warehouse (Internal)
→ Confirm replenishment
      │
      └─► Odoo auto-creates a stock.picking (type = internal)
              └─► When picking is Validated → same flow as above
```

---

## Viewing the Journal Entry

After validation, on the **Transfer form**:

- A **📖 Journal Entry** smart button appears in the top-right
- A **Transfer Journal Entry** tab is added to the notebook
- Clicking the smart button opens the full `account.move` form

---

## Amount Calculation Logic

```python
# For each done move line:
amount += qty_done × product.standard_price

# If all standard_price = 0 → uses qty_done × 1.0 (fallback)
# If amount = 0 → journal entry is SKIPPED (logged as warning)
```

---

## FAQ

**Q: Will duplicate entries be created if I validate multiple times?**  
A: No. The code checks `internal_transfer_move_id` first. If an entry already exists it skips creation.

**Q: What if the product has no cost (standard_price = 0)?**  
A: A fallback of `qty × 1.0` is used so an entry is always created. You can change product costs in **Inventory → Products → Cost**.

**Q: Does this work with multi-company?**  
A: Yes. Journal and account are stored per `res.company`. Each company can have its own settings.

**Q: What if I don't have `account` module installed?**  
A: This module declares `account` as a dependency. Odoo will install it automatically if not already installed.

---

## Technical Notes

| Item | Detail |
|------|--------|
| Hook point | `stock.picking._action_done()` (super() called first) |
| JE type | `account.move` with `move_type = 'entry'` |
| JE state | Auto-posted (`action_post()`) immediately |
| Errors | Caught and logged; transfer validation is NOT blocked |
| Sudo | JE created with `sudo()` to avoid permission issues |

---

## Author

Custom Development — Odoo 19 CE  
License: LGPL-3
