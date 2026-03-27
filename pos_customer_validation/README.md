# POS Customer Validation Module

A custom Odoo 19 CE module that enforces customer selection before allowing payment processing in the Point of Sale (POS) system.

## Features

✅ **Customer Validation**: Prevents payment processing without a selected customer  
✅ **User-Friendly Popup**: Displays a clear warning message when no customer is selected  
✅ **Configurable**: Can be enabled/disabled and customized per POS configuration  
✅ **Works with Cash KDTY and Card KDTY**: Specifically targets these payment methods  
✅ **Odoo 19 CE Compatible**: Built with the latest Odoo framework and OWL widgets

## Installation Steps

### Step 1: Copy the Module
Copy the `pos_customer_validation` folder to your Odoo addons directory:
```bash
cp -r pos_customer_validation /path/to/odoo/addons/
```

Common addon paths:
- `/opt/odoo/addons/`
- `/var/lib/odoo/addons/`
- Your custom addons folder

### Step 2: Update Module List
1. Go to **Apps** section in Odoo
2. Click **Update Apps List** (Refresh icon)
3. Search for "POS Customer Validation"
4. Click **Install**

### Step 3: Configuration
1. Navigate to **Point of Sale > Configuration > POS Configurations**
2. Open your POS configuration
3. Go to the **Customer Validation** tab
4. Enable **"Require Customer for Payment"**
5. (Optional) Select specific payment methods requiring customer selection
6. Save

### Step 4: Restart POS Session
- Close and reopen your POS session for changes to take effect
- Go to **Point of Sale > New Session**

## File Structure

```
pos_customer_validation/
├── __init__.py                      # Module initialization
├── __manifest__.py                  # Module manifest/configuration
├── models/
│   ├── __init__.py
│   └── pos_config.py               # POS configuration model
├── views/
│   └── pos_config_views.xml        # POS config form view
└── static/
    ├── src/
    │   ├── js/
    │   │   └── payment_validation.js  # Main validation logic
    │   ├── xml/
    │   │   └── payment_popup.xml      # Popup template
    │   └── css/
    │       └── style.css              # Popup styling
    └── description/
        └── icon.png                  # Module icon
```

## How It Works

### Technical Flow

1. **Payment Screen Access**: User navigates to the Payment screen in POS
2. **Payment Method Click**: User clicks on "Cash KDTY" or "Card KDTY"
3. **Customer Check**: JavaScript code checks if a customer is selected
4. **Validation Result**:
   - ✅ **Customer Selected**: Proceeds with payment normally
   - ❌ **No Customer**: Displays popup warning and blocks payment

### Code Highlights

**JavaScript Validation** (`payment_validation.js`):
```javascript
const currentClient = this.pos.get_client();

if (!currentClient) {
    this.env.services.dialog.add(AlertDialog, {
        title: 'Missing Customer',
        body: 'Please select a customer before proceeding with payment.',
    });
    return;
}
```

## Customization Guide

### Change Popup Message
Edit `payment_validation.js` and update the dialog body:
```javascript
body: 'Your custom message here',
```

### Add Additional Payment Methods
Modify the validation logic in `payment_validation.js` to check specific payment methods:
```javascript
if (paymentMethod.name === 'Cash KDTY' || paymentMethod.name === 'Card KDTY') {
    // Perform validation
}
```

### Customize Popup Styling
Edit `style.css` to match your brand colors:
```css
.popup-header {
    background: linear-gradient(135deg, #YOUR_COLOR_1, #YOUR_COLOR_2);
}
```

## Troubleshooting

### Issue: Module not appearing in Apps list
**Solution**: 
- Ensure the module folder is in a valid addons directory
- Check that `__manifest__.py` is properly formatted
- Run `odoo-bin -u base` to refresh modules

### Issue: Popup not showing
**Solution**:
- Clear browser cache (Ctrl+Shift+Delete)
- Restart POS session
- Check browser console for JavaScript errors (F12 > Console)

### Issue: Validation not working
**Solution**:
- Verify module is installed (Apps > Search "Customer Validation")
- Check POS Configuration has "Require Customer for Payment" enabled
- Ensure you're using Odoo 19 CE

### Issue: JavaScript errors in console
**Solution**:
- Verify all files are in the correct directories
- Check XML syntax in manifest and view files
- Ensure proper permissions on module folder

## Browser Compatibility

- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Database Compatibility

- ✅ PostgreSQL 12+
- ✅ PostgreSQL 13+
- ✅ PostgreSQL 14+

## Odoo Versions

- ✅ **Odoo 19 CE** (Fully supported)
- ⚠️ **Odoo 18 and below** (May require modifications)

## Support and Issues

If you encounter any issues:
1. Check the troubleshooting section above
2. Verify all files are in correct locations
3. Review browser console for error messages
4. Check Odoo server logs: `/var/log/odoo/odoo-server.log`

## License

LGPL-3 (GNU Lesser General Public License v3)

## Author

Your Company Name

---

**Version**: 1.0  
**Last Updated**: 2026  
**Odoo Version**: 19 CE
