# POS Cash Transfer Between Counters
### Custom Module for Odoo 19 Community Edition
### Developed for: FON-STORE

---

## 📦 What This Module Does

Allows cashiers/managers to transfer cash directly from one POS counter 
to another open POS counter — all from inside the POS interface.

---

## ✅ Features

- Transfer cash between any two open POS sessions
- Transfer button inside POS menu
- Shows all currently open counters as destination
- Automatic Cash In / Cash Out statement entries
- Complete transfer history in backend
- Transfer reference number (PCT/2025/0001)
- Reason/notes for each transfer
- Manager can view all transfers under POS → Cash Transfers menu

---

## 🛠️ Installation Steps

### Step 1: Upload Module to Server
Copy the `pos_cash_transfer` folder to your Odoo addons directory:
```
/odoo/addons/pos_cash_transfer/
```
OR your custom addons path (check odoo.conf for `addons_path`)

### Step 2: Restart Odoo Service
```bash
sudo systemctl restart odoo
# OR
sudo service odoo restart
```

### Step 3: Activate Developer Mode in Odoo
- Go to Settings → scroll down → Activate Developer Mode

### Step 4: Update Apps List
- Go to Apps menu → Click "Update Apps List"

### Step 5: Install the Module
- Search for "POS Cash Transfer"
- Click Install ✅

---

## ⚙️ Configuration After Install

1. Go to **POS → Configuration → Point of Sale**
2. Open any counter (e.g., CHELARI COUNTER 1)
3. Click **"Configurations > Settings"**
4. You will see new option: **"Cash Transfer Between Counters"** ✅
5. Enable it → Save

---

## 🚀 How to Use in POS

1. Open Register on Counter 1
2. Click **☰ Menu** (top right)
3. Click **"Cash Transfer"** button
4. A popup appears:
   - Select **destination counter** (e.g., Counter 2)
   - Enter **amount** (e.g., ₹ 5000)
   - Enter **reason** (e.g., "Counter 2 needs change")
5. Click **"Transfer Now"**
6. ✅ Cash is transferred!

---

## 📊 View Transfer History

- Go to **Point of Sale → Cash Transfers** (new menu)
- Filter by date, counter, cashier
- See all transfers IN and OUT per session

---

## 📁 Module Structure

```
pos_cash_transfer/
├── __manifest__.py          → Module info
├── __init__.py
├── models/
│   ├── pos_cash_transfer.py → Main transfer model
│   └── pos_config.py        → POS settings extension
├── controllers/
│   └── main.py              → HTTP/JSON RPC endpoints
├── views/
│   ├── pos_cash_transfer_views.xml → Backend views & menus
│   └── pos_config_views.xml        → POS settings view
├── security/
│   └── ir.model.access.csv  → Access rights
├── data/
│   └── sequence.xml         → Transfer reference sequence
└── static/src/
    ├── js/
    │   ├── CashTransferButton.js  → POS button component
    │   └── CashTransferPopup.js   → POS popup component
    ├── xml/
    │   └── CashTransferPopup.xml  → POS templates
    └── css/
        └── pos_cash_transfer.css  → Styling
```

---

## ⚠️ Requirements

- Odoo 19 Community Edition
- Point of Sale module installed
- Accounting module installed
- Each POS must have a Cash payment method configured

---

## 🇮🇳 Support
Custom developed for FON-STORE, Malappuram, Kerala
