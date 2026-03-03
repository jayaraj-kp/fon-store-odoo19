# POS UPI QR Code on Receipt
### Odoo 19 Community Edition — Custom Module

---

## What this module does

Adds a **dynamic UPI payment QR code** to every POS receipt.

- The QR encodes a UPI deep-link with the **exact bill amount** pre-filled
- Customers scan with **Google Pay, PhonePe, Paytm, BHIM** or any UPI app
- Payment is completed instantly on the customer's phone
- No third-party payment gateway needed

---

## Installation

### Step 1 — Install the Python qrcode library

Run on your Odoo server:

```bash
pip install "qrcode[pil]"
```

> This is required for the server to generate QR PNG images.

### Step 2 — Copy module into Odoo addons path

```bash
cp -r custom_pos_upi_qr /path/to/your/odoo/addons/
```

### Step 3 — Update apps list & install

1. Restart Odoo server
2. Go to **Apps → Update Apps List**
3. Search for **"POS UPI QR Code"**
4. Click **Install**

---

## Configuration

1. Go to **Point of Sale → Configuration → Settings**
2. Select your POS in the top dropdown
3. Scroll to the **Bills & Receipts** section
4. Enable **"Show UPI QR Code on Receipt"**
5. Enter your **UPI ID (VPA)** — e.g. `yourstore@paytm` or `9876543210@ybl`
6. Enter **UPI Merchant Name** — the name customers see in their UPI app
7. Click **Save**
8. Close & reopen the POS session

---

## How it works (technical)

| Layer | File | Purpose |
|---|---|---|
| Python model | `models/pos_config.py` | Adds 3 fields to `pos.config` |
| Python controller | `controllers/main.py` | `/pos/upi_qr` route → returns QR PNG |
| JS patch | `static/src/app/upi_qr_receipt.js` | Patches `OrderReceipt` OWL component |
| OWL template | `static/src/app/upi_qr_receipt.xml` | Injects QR block into receipt XML |
| CSS | `static/src/css/upi_qr.css` | Styles + print media query |
| View | `views/pos_config_views.xml` | UPI fields in POS Settings form |

The UPI QR URL format used:
```
upi://pay?pa=<VPA>&pn=<MerchantName>&am=<Amount>&cu=INR&tn=POS+Payment
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| QR not appearing on receipt | Ensure "Show UPI QR on Receipt" is enabled in POS Settings |
| Blank/broken QR image | Run `pip install "qrcode[pil]"` on the server and restart Odoo |
| Wrong amount on QR | The amount is taken from `total_with_tax` — verify GST settings |
| Template xpath error | Check Odoo 19 receipt template structure; see note below |

> **Note on template xpath**: If the QR block does not appear, the Odoo 19 `OrderReceipt`
> template structure may differ slightly. Open browser dev tools, inspect the receipt DOM,
> find the `.pos-receipt` div, and verify the xpath in `upi_qr_receipt.xml` still applies.

---

## License
LGPL-3
