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
#!/usr/bin/env python3
"""
DEEP DIAGNOSTIC - Run in Odoo shell:
    python odoo-bin shell -d Test_DB

This will tell us EXACTLY which method creates the invoice line
with account 110100, so we know the correct override point.
"""

print("=" * 65)
print("DEEP POS INVOICE DIAGNOSTIC")
print("=" * 65)

# ── 1. Find the latest POS invoice with 110100 ──────────────────────
print("\n[1] LATEST INVOICE WITH STOCK VALUATION (110100):")
valuation_acct = env['account.account'].search([('code', '=', '110100')], limit=1)
if not valuation_acct:
    print("  110100 account not found!")
else:
    print(f"  Found account: {valuation_acct.code} {valuation_acct.name} (id={valuation_acct.id})")
    lines = env['account.move.line'].search([
        ('account_id', '=', valuation_acct.id),
        ('move_id.move_type', '=', 'out_invoice'),
    ], order='id desc', limit=3)
    for line in lines:
        inv = line.move_id
        print(f"\n  Invoice: {inv.name} | pos_order_ids: {inv.pos_order_ids.mapped('name') if hasattr(inv, 'pos_order_ids') else 'N/A'}")
        print(f"  Product: {line.product_id.name} | account: {line.account_id.code}")

# ── 2. Check if _prepare_invoice_line is our version ────────────────
print("\n[2] WHICH MODULE OWNS _prepare_invoice_line ON pos.order:")
import inspect
PosOrder = env['pos.order'].__class__
mro = PosOrder.__mro__
for cls in mro:
    if '_prepare_invoice_line' in cls.__dict__:
        print(f"  Found in: {cls.__module__}.{cls.__name__}")

# ── 3. Check if our account_move module is loaded ───────────────────
print("\n[3] MODULE REGISTRY CHECK:")
# Check if PosOrderAccountFix class exists in registry
classes_found = []
for cls in mro:
    if 'PosOrderAccountFix' in cls.__name__ or 'anglo' in cls.__module__.lower():
        classes_found.append(f"{cls.__module__}.{cls.__name__}")
if classes_found:
    print("  Anglo-Saxon classes in pos.order MRO:")
    for c in classes_found:
        print(f"    {c}")
else:
    print("  ❌ NO Anglo-Saxon classes found in pos.order MRO!")
    print("     This means account_move.py is NOT loaded or PosOrderAccountFix")
    print("     is not being picked up by the registry.")

# ── 4. Check AccountMoveLine MRO ────────────────────────────────────
print("\n[4] AccountMoveLine MRO (looking for our fix):")
AML = env['account.move.line'].__class__
aml_mro = AML.__mro__
for cls in aml_mro:
    if 'anglo' in cls.__module__.lower() or 'AccountMoveLineFix' in cls.__name__:
        print(f"  Found: {cls.__module__}.{cls.__name__}")

# ── 5. Check HOW the invoice was created - trace pos_order ──────────
print("\n[5] POS SESSION INVOICE CREATION METHOD:")
PosSession = env['pos.session'].__class__
session_mro = PosSession.__mro__
for cls in session_mro:
    if '_create_account_move' in cls.__dict__:
        print(f"  _create_account_move in: {cls.__module__}.{cls.__name__}")
    if '_prepare_invoice_line' in cls.__dict__:
        print(f"  _prepare_invoice_line in: {cls.__module__}.{cls.__name__}")

# ── 6. Check what method builds lines for session invoices ──────────
print("\n[6] TRACING invoice line creation for POS session:")
for cls in mro:
    methods = [m for m in cls.__dict__ if 'invoice' in m.lower() or 'account' in m.lower()]
    if methods and 'anglo' in cls.__module__.lower():
        print(f"  {cls.__module__}: {methods}")

# ── 7. Check installed module state ─────────────────────────────────
print("\n[7] MODULE STATE:")
for mod_name in ['stock_anglo_saxon_ce19', 'stock_account_category_fix']:
    mod = env['ir.module.module'].search([('name', '=', mod_name)], limit=1)
    if mod:
        print(f"  {mod_name}: {mod.state} (latest_version={mod.latest_version})")
    else:
        print(f"  {mod_name}: NOT FOUND")

# ── 8. Check if _prepare_invoice_line actually fires ────────────────
print("\n[8] MONKEY-PATCH TEST (simulate _prepare_invoice_line call):")
# Get a recent POS order
pos_order = env['pos.order'].search([('state', '=', 'done')], order='id desc', limit=1)
if pos_order and pos_order.lines:
    line = pos_order.lines[0]
    print(f"  Testing with order: {pos_order.name}, line product: {line.product_id.name}")
    try:
        vals = pos_order._prepare_invoice_line(line)
        acct_id = vals.get('account_id')
        acct = env['account.account'].browse(acct_id) if acct_id else None
        print(f"  _prepare_invoice_line returned account_id: {acct_id}")
        print(f"  Account: {acct.code + ' ' + acct.name if acct else 'NOT FOUND'}")
        if acct and acct.id == valuation_acct.id:
            print("  ❌ STILL returning Stock Valuation account!")
            print("     Our fix is NOT intercepting this method.")
        else:
            print("  ✅ Returning a different account (fix may be working)")
    except Exception as e:
        print(f"  ERROR calling _prepare_invoice_line: {e}")

print("\n" + "=" * 65)
print("Share this full output to pinpoint the exact fix needed.")
print("=" * 65)