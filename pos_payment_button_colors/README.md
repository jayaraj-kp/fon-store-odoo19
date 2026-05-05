# POS Payment Button Colors

Custom Odoo 19 Community Edition module that adds **distinct colors** to the
`Cash KDTY` and `Card KDTY` one-click payment buttons in Point of Sale.

## Button Colors

| Button      | Color  | Hex       |
|-------------|--------|-----------|
| Cash KDTY   | 🟢 Green | `#27ae60` |
| Card KDTY   | 🔵 Blue  | `#2980b9` |

Both buttons also get:
- Hover & active states with depth shadow
- Emoji icon prefix (💵 cash, 💳 card)
- Uppercase bold text
- Rounded corners

## Installation

1. Copy the `pos_payment_button_colors` folder into your Odoo **addons** path.
2. Restart the Odoo server.
3. Go to **Apps** → search `POS Payment Button Colors` → **Install**.
4. Open Point of Sale — the buttons are styled automatically.

## Requirements

- Odoo 19 Community Edition
- `point_of_sale` module installed

## Notes

The module uses a DOM MutationObserver to detect buttons by their **text label**
(`Cash KDTY` / `Card KDTY`), so it works regardless of how Odoo renders the
payment method list. No database changes are made.
