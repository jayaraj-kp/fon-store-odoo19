#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT — Run this in Odoo shell to find the real issue.

HOW TO RUN:
    cd /path/to/odoo
    python odoo-bin shell -d YOUR_DATABASE_NAME

Then paste the code below into the shell and press Enter.
"""

# ============================================================
# PASTE THIS INTO YOUR ODOO SHELL (python odoo-bin shell -d DBNAME)
# ============================================================

print("=" * 60)
print("ANGLO-SAXON DIAGNOSTIC REPORT")
print("=" * 60)

# 1. Check all product categories and their valuation settings
print("\n[1] PRODUCT CATEGORIES WITH VALUATION INFO:")
cats = env['product.category'].search([])
for cat in cats:
    val = cat.property_valuation
    cost = cat.property_cost_method
    # Check our custom fields
    val_acct = getattr(cat, 'property_stock_valuation_account_id', 'FIELD MISSING')
    inp_acct = getattr(cat, 'property_stock_account_input_categ_id', 'FIELD MISSING')
    print(f"  Category: '{cat.name}'")
    print(f"    property_valuation      = '{val}'   (raw value)")
    print(f"    property_cost_method    = '{cost}'")
    print(f"    stock_valuation_account = {val_acct.name if hasattr(val_acct, 'name') else val_acct}")
    print(f"    stock_input_account     = {inp_acct.name if hasattr(inp_acct, 'name') else inp_acct}")
    print()

# 2. Check the AVCO NON category specifically
print("\n[2] AVCO NON CATEGORY DETAILS:")
avco = env['product.category'].search([('name', '=', 'AVCO NON')], limit=1)
if avco:
    print(f"  property_valuation raw value: '{avco.property_valuation}'")
    print(f"  Is it 'real_time'?  {avco.property_valuation == 'real_time'}")
    print(f"  Is it 'perpetual_invoicing'?  {avco.property_valuation == 'perpetual_invoicing'}")
    print(f"  All fields: {avco.read()}")
else:
    print("  NOT FOUND!")

# 3. Check latest draft vendor bill
print("\n[3] LATEST VENDOR BILL STATUS:")
bills = env['account.move'].search([('move_type', '=', 'in_invoice')], order='id desc', limit=3)
for bill in bills:
    print(f"  Bill: {bill.name} | State: {bill.state}")
    for line in bill.invoice_line_ids.filtered(lambda l: l.product_id):
        cat = line.product_id.categ_id
        print(f"    Product: {line.product_id.name}")
        print(f"    Category: {cat.name}")
        print(f"    property_valuation: '{cat.property_valuation}'")
        print(f"    standard_price: {line.product_id.standard_price}")

# 4. Check if our module is installed
print("\n[4] MODULE INSTALLATION STATUS:")
modules = env['ir.module.module'].search([
    ('name', 'in', ['stock_anglo_saxon_ce19', 'stock_account_category_fix'])
])
for m in modules:
    print(f"  {m.name}: {m.state}")

print("\n" + "=" * 60)
print("Copy the output above and share it to diagnose the issue.")
print("=" * 60)
