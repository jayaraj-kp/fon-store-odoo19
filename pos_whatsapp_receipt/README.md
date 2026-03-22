# POS WhatsApp Receipt — Odoo 19 CE Custom Module

Automatically sends POS receipts to customers via WhatsApp immediately after a transaction is completed.

---

## Features

- ✅ Auto-send WhatsApp receipt on payment confirmation
- 📲 Manual "Send WhatsApp Receipt" button on the POS Receipt Screen
- 🔘 Manual resend button on backend POS Order form
- 📋 Full message log with sent/failed status
- 🛠️ Supports **Meta WhatsApp Business Cloud API** (free tier available) and **Twilio**
- ✏️ Fully customizable message template with placeholders
- 🇮🇳 Defaults to India (+91) for 10-digit numbers (configurable)

---

## Installation

1. Copy the `pos_whatsapp_receipt` folder into your Odoo `addons` path.
2. Restart the Odoo service.
3. Go to **Settings → Apps**, search for "POS WhatsApp Receipt", and install.

---

## Configuration

Go to **Point of Sale → Configuration → Settings**, scroll to **WhatsApp Receipt Settings**.

### Option A: Meta WhatsApp Business Cloud API (Recommended — Free tier)

1. Go to [https://developers.facebook.com](https://developers.facebook.com) → Create App → Business → WhatsApp
2. Under **WhatsApp → API Setup**, note:
   - **Access Token** (temporary or permanent)
   - **Phone Number ID**
3. Add a test number or use a verified business number
4. Paste both values into Odoo Settings

### Option B: Twilio WhatsApp

1. Sign up at [https://www.twilio.com](https://www.twilio.com)
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Note your **Account SID**, **Auth Token**, and sandbox number (`whatsapp:+14155238886`)
4. Paste into Odoo Settings

---

## How It Works

1. Cashier selects a customer with a mobile/phone number in POS
2. After payment is confirmed, Odoo automatically sends the receipt to that number
3. If auto-send fails or there's no phone number, the cashier can tap **📲 Send WhatsApp Receipt** on the receipt screen
4. Managers can view all logs under **Point of Sale → WhatsApp Logs**

---

## Phone Number Format

- 10-digit Indian numbers (e.g. `9876543210`) → auto-prefixed with `+91`
- Numbers with `+` prefix are sent as-is
- Non-digit characters are stripped automatically

To change the default country code, edit `_normalize_phone()` in `models/pos_order.py`:
```python
digits = '91' + digits   # Change 91 to your country code
```

---

## Message Template Placeholders

| Placeholder | Description |
|---|---|
| `{customer_name}` | Customer's name |
| `{order_ref}` | POS order reference number |
| `{date}` | Transaction date & time |
| `{order_lines}` | Itemised list of products |
| `{currency}` | Currency symbol |
| `{total}` | Order total |
| `{company_name}` | Your company name |

---

## File Structure

```
pos_whatsapp_receipt/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── pos_order.py          ← Core send logic + auto-hook
│   ├── pos_whatsapp_log.py   ← Log model
│   └── res_config_settings.py
├── views/
│   ├── res_config_settings_views.xml
│   └── pos_whatsapp_log_views.xml
├── static/src/
│   ├── js/
│   │   ├── whatsapp_button.js   ← POS frontend button
│   │   └── whatsapp_button.xml  ← OWL template
│   └── css/
│       └── whatsapp.css
├── data/
│   └── ir_sequence_data.xml
└── security/
    └── ir.model.access.csv
```
