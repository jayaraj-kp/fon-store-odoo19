# ═══════════════════════════════════════════════════════════════════
# HELPER: Run this in Odoo Shell or Technical > Server Actions
# to find the correct kanban view XML ID on YOUR Odoo version.
#
# Go to: Settings > Technical > Actions > Server Actions > New
# Model: ir.ui.view  |  Action: Execute Python Code
# Paste the code below and click Run
# ═══════════════════════════════════════════════════════════════════

views = env['ir.ui.view'].search([
    ('model', '=', 'stock.picking.type'),
    ('type', '=', 'kanban'),
])

for v in views:
    print(f"XML ID : {v.get_external_id().get(v.id, 'NO XML ID')}")
    print(f"Name   : {v.name}")
    print(f"DB id  : {v.id}")
    print("─" * 50)

# ═══════════════════════════════════════════════════════════════════
# EXPECTED OUTPUT (Odoo 16):
#   XML ID: stock.view_picking_type_kanban
#
# EXPECTED OUTPUT (Odoo 17/18/19):
#   XML ID: stock.stock_picking_type_kanban
#
# Then open views/stock_warehouse_dashboard_views.xml and change:
#   <field name="inherit_id" ref="stock.YOUR_XML_ID_HERE"/>
# ═══════════════════════════════════════════════════════════════════
