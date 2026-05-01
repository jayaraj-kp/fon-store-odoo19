# #!/usr/bin/env python3
# """
# DIAGNOSTIC SCRIPT — Run this in Odoo shell to find the real issue.
#
# HOW TO RUN:
#     cd /path/to/odoo
#     python odoo-bin shell -d YOUR_DATABASE_NAME
#
# Then paste the code below into the shell and press Enter.
# """
#
# # ============================================================
# # PASTE THIS INTO YOUR ODOO SHELL (python odoo-bin shell -d DBNAME)
# # ============================================================
#
# print("=" * 60)
# print("ANGLO-SAXON DIAGNOSTIC REPORT")
# print("=" * 60)
#
# # 1. Check all product categories and their valuation settings
# print("\n[1] PRODUCT CATEGORIES WITH VALUATION INFO:")
# cats = env['product.category'].search([])
# for cat in cats:
#     val = cat.property_valuation
#     cost = cat.property_cost_method
#     # Check our custom fields
#     val_acct = getattr(cat, 'property_stock_valuation_account_id', 'FIELD MISSING')
#     inp_acct = getattr(cat, 'property_stock_account_input_categ_id', 'FIELD MISSING')
#     print(f"  Category: '{cat.name}'")
#     print(f"    property_valuation      = '{val}'   (raw value)")
#     print(f"    property_cost_method    = '{cost}'")
#     print(f"    stock_valuation_account = {val_acct.name if hasattr(val_acct, 'name') else val_acct}")
#     print(f"    stock_input_account     = {inp_acct.name if hasattr(inp_acct, 'name') else inp_acct}")
#     print()
#
# # 2. Check the AVCO NON category specifically
# print("\n[2] AVCO NON CATEGORY DETAILS:")
# avco = env['product.category'].search([('name', '=', 'AVCO NON')], limit=1)
# if avco:
#     print(f"  property_valuation raw value: '{avco.property_valuation}'")
#     print(f"  Is it 'real_time'?  {avco.property_valuation == 'real_time'}")
#     print(f"  Is it 'perpetual_invoicing'?  {avco.property_valuation == 'perpetual_invoicing'}")
#     print(f"  All fields: {avco.read()}")
# else:
#     print("  NOT FOUND!")
#
# # 3. Check latest draft vendor bill
# print("\n[3] LATEST VENDOR BILL STATUS:")
# bills = env['account.move'].search([('move_type', '=', 'in_invoice')], order='id desc', limit=3)
# for bill in bills:
#     print(f"  Bill: {bill.name} | State: {bill.state}")
#     for line in bill.invoice_line_ids.filtered(lambda l: l.product_id):
#         cat = line.product_id.categ_id
#         print(f"    Product: {line.product_id.name}")
#         print(f"    Category: {cat.name}")
#         print(f"    property_valuation: '{cat.property_valuation}'")
#         print(f"    standard_price: {line.product_id.standard_price}")
#
# # 4. Check if our module is installed
# print("\n[4] MODULE INSTALLATION STATUS:")
# modules = env['ir.module.module'].search([
#     ('name', 'in', ['stock_anglo_saxon_ce19', 'stock_account_category_fix'])
# ])
# for m in modules:
#     print(f"  {m.name}: {m.state}")
#
# print("\n" + "=" * 60)
# print("Copy the output above and share it to diagnose the issue.")
# print("=" * 60)
#!/usr/bin/env python3
"""
DIAGNOSTIC: Verify POS Invoice Account Fix
==========================================
Run in Odoo shell:
    python odoo-bin shell -d YOUR_DB

Paste all code below into the shell.
"""

print("=" * 65)
print("POS INVOICE ACCOUNT FIX — DIAGNOSTIC")
print("=" * 65)

# ── 1. Check product category accounts ──────────────────────────────
print("\n[1] PRODUCT CATEGORY ACCOUNT CONFIGURATION:")
cats = env['product.category'].search([])
ok = True
for cat in cats:
    val = cat.property_valuation
    val_str = list(val.values())[0] if isinstance(val, dict) and val else str(val)
    if val_str not in ('real_time', 'perpetual', 'perpetual_invoicing'):
        continue  # skip non-perpetual

    val_acct = getattr(cat, 'property_stock_valuation_account_id', False)
    out_acct = getattr(cat, 'property_stock_account_output_categ_id', False)
    inp_acct = getattr(cat, 'property_stock_account_input_categ_id', False)

    print(f"\n  Category: '{cat.name}' [{val_str}]")
    print(f"    Stock Valuation : {val_acct.code + ' ' + val_acct.name if val_acct else '❌ NOT SET'}")
    print(f"    Stock Output    : {out_acct.code + ' ' + out_acct.name if out_acct else '❌ NOT SET'}")
    print(f"    Stock Input     : {inp_acct.code + ' ' + inp_acct.name if inp_acct else '❌ NOT SET'}")

    if not val_acct or not out_acct:
        print("    ⚠️  WARNING: Missing accounts — POS fix will be SKIPPED for this category!")
        ok = False

if ok:
    print("\n  ✅ All perpetual categories have required accounts.")

# ── 2. Check latest POS invoices ────────────────────────────────────
print("\n[2] LAST 5 POS-RELATED CUSTOMER INVOICES (Journal Items):")
invoices = env['account.move'].search([
    ('move_type', '=', 'out_invoice'),
], order='id desc', limit=5)

for inv in invoices:
    print(f"\n  Invoice: {inv.name} | State: {inv.state}")
    for line in inv.line_ids:
        print(f"    Account: {line.account_id.code} {line.account_id.name:30s} "
              f"DR: {line.debit:>10.2f}  CR: {line.credit:>10.2f}  "
              f"Product: {line.product_id.name or '-'}")

# ── 3. Simulate _prepare_invoice_line fix ───────────────────────────
print("\n[3] SIMULATING POS INVOICE LINE FIX:")
# Find a storable product with a perpetual category
product = env['product.product'].search([
    ('type', '=', 'consu'),
], limit=1)

if product:
    categ = product.categ_id
    val = categ.property_valuation
    val_str = list(val.values())[0] if isinstance(val, dict) and val else str(val)
    val_acct = getattr(categ, 'property_stock_valuation_account_id', False)
    out_acct = getattr(categ, 'property_stock_account_output_categ_id', False)

    print(f"  Product: {product.name}")
    print(f"  Category: {categ.name} [{val_str}]")
    print(f"  Valuation account: {val_acct.code + ' ' + val_acct.name if val_acct else 'NOT SET'}")
    print(f"  Output account:    {out_acct.code + ' ' + out_acct.name if out_acct else 'NOT SET'}")

    if val_str in ('real_time', 'perpetual', 'perpetual_invoicing') and val_acct and out_acct:
        if val_acct.id != out_acct.id:
            print(f"\n  ✅ Fix WILL work: {val_acct.code} → {out_acct.code}")
        else:
            print(f"\n  ⚠️  Valuation and Output account are THE SAME. Check configuration.")
    else:
        print(f"\n  ⚠️  Fix conditions not met for this product.")
else:
    print("  No storable product found to test with.")

# ── 4. Check module is installed ────────────────────────────────────
print("\n[4] MODULE STATUS:")
mods = env['ir.module.module'].search([
    ('name', 'in', [
        'stock_anglo_saxon_ce19',
        'stock_account_category_fix',
    ])
])
for m in mods:
    print(f"  {m.name}: {m.state}")

print("\n" + "=" * 65)
print("If [3] shows ✅ and [1] shows no ❌, the fix should work.")
print("Create a new POS order AFTER upgrading the module to test.")
print("=" * 65)