# # -*- coding: utf-8 -*-
# # Migration: 19.0.1.0.0 → 19.0.2.0.0
# # Initialises wh_send_state on existing stock.picking records.
# #
# # NOTE: picking_type_code is a computed ORM field — it does NOT exist as a
# # real DB column. The actual column lives in stock_picking_type.code.
# # We join stock_picking_type to filter internal transfers.
#
# def migrate(cr, version):
#     if not version:
#         return
#
#     # 1. Add the column (safe if already exists)
#     cr.execute("""
#         ALTER TABLE stock_picking
#         ADD COLUMN IF NOT EXISTS wh_send_state VARCHAR DEFAULT 'na';
#     """)
#
#     # 2. Ensure no NULLs
#     cr.execute("""
#         UPDATE stock_picking
#         SET wh_send_state = 'na'
#         WHERE wh_send_state IS NULL;
#     """)
#
#     # 3. Mark active cross-WH internal transfers as 'pending'
#     cr.execute("""
#         UPDATE stock_picking sp
#         SET wh_send_state = 'pending'
#         FROM stock_picking_type spt
#         WHERE spt.id = sp.picking_type_id
#           AND spt.code = 'internal'
#           AND sp.state IN ('confirmed', 'assigned')
#           AND sp.wh_send_state = 'na'
#           AND EXISTS (
#               SELECT 1 FROM stock_location src_loc
#               WHERE src_loc.id = sp.location_id
#                 AND src_loc.warehouse_id IS NOT NULL
#           )
#           AND EXISTS (
#               SELECT 1 FROM stock_location dst_loc
#               WHERE dst_loc.id = sp.location_dest_id
#                 AND dst_loc.warehouse_id IS NOT NULL
#           )
#           AND (
#               SELECT src_loc.warehouse_id FROM stock_location src_loc
#               WHERE src_loc.id = sp.location_id
#           ) != (
#               SELECT dst_loc.warehouse_id FROM stock_location dst_loc
#               WHERE dst_loc.id = sp.location_dest_id
#           );
#     """)
#
#     # 4. Mark already-validated cross-WH internal transfers as 'accepted'
#     cr.execute("""
#         UPDATE stock_picking sp
#         SET wh_send_state = 'accepted'
#         FROM stock_picking_type spt
#         WHERE spt.id = sp.picking_type_id
#           AND spt.code = 'internal'
#           AND sp.state = 'done'
#           AND sp.wh_send_state = 'na'
#           AND EXISTS (
#               SELECT 1 FROM stock_location src_loc
#               WHERE src_loc.id = sp.location_id
#                 AND src_loc.warehouse_id IS NOT NULL
#           )
#           AND EXISTS (
#               SELECT 1 FROM stock_location dst_loc
#               WHERE dst_loc.id = sp.location_dest_id
#                 AND dst_loc.warehouse_id IS NOT NULL
#           )
#           AND (
#               SELECT src_loc.warehouse_id FROM stock_location src_loc
#               WHERE src_loc.id = sp.location_id
#           ) != (
#               SELECT dst_loc.warehouse_id FROM stock_location dst_loc
#               WHERE dst_loc.id = sp.location_dest_id
#           );
#     """)
# -*- coding: utf-8 -*-
# Migration: 19.0.1.0.0 → 19.0.2.0.0
# Initialises wh_send_state on existing stock.picking records.
#
# NOTE: picking_type_code is a computed ORM field — it does NOT exist as a
# real DB column. The actual column lives in stock_picking_type.code.
# We join stock_picking_type to filter internal transfers.
#
# v2 changes vs v1:
#   - Also covers 'waiting' state (replenishment transfers start here)
#   - Cross-WH detection uses a recursive CTE to resolve warehouse via
#     parent location chain — handles transit locations with no direct
#     warehouse_id on the location row itself.

def migrate(cr, version):
    if not version:
        return

    # 1. Add the column (safe if already exists)
    cr.execute("""
        ALTER TABLE stock_picking
        ADD COLUMN IF NOT EXISTS wh_send_state VARCHAR DEFAULT 'na';
    """)

    # 2. Ensure no NULLs
    cr.execute("""
        UPDATE stock_picking
        SET wh_send_state = 'na'
        WHERE wh_send_state IS NULL;
    """)

    # ── Recursive CTE to resolve warehouse_id by walking up location tree ──
    # stock_location.location_id is the parent FK (NULL at root).
    # We walk up until we find a row with warehouse_id IS NOT NULL.
    CROSS_WH_CTE = """
        WITH RECURSIVE loc_wh AS (
            -- Base: locations that directly belong to a warehouse
            SELECT id, warehouse_id
            FROM stock_location
            WHERE warehouse_id IS NOT NULL

            UNION ALL

            -- Step: locations whose parent resolves to a warehouse
            SELECT sl.id, lw.warehouse_id
            FROM stock_location sl
            JOIN loc_wh lw ON sl.location_id = lw.id
            WHERE sl.warehouse_id IS NULL
        )
    """

    # 3. Mark active cross-WH internal transfers as 'pending'
    #    Covers confirmed, assigned, AND waiting states (replenishment uses 'waiting')
    cr.execute(CROSS_WH_CTE + """
        UPDATE stock_picking sp
        SET wh_send_state = 'pending'
        FROM stock_picking_type spt
        JOIN loc_wh src_wh ON src_wh.id = sp.location_id
        JOIN loc_wh dst_wh ON dst_wh.id = sp.location_dest_id
        WHERE spt.id = sp.picking_type_id
          AND spt.code = 'internal'
          AND sp.state IN ('waiting', 'confirmed', 'assigned')
          AND sp.wh_send_state = 'na'
          AND src_wh.warehouse_id IS NOT NULL
          AND dst_wh.warehouse_id IS NOT NULL
          AND src_wh.warehouse_id != dst_wh.warehouse_id;
    """)

    # 4. Mark already-validated cross-WH internal transfers as 'accepted'
    cr.execute(CROSS_WH_CTE + """
        UPDATE stock_picking sp
        SET wh_send_state = 'accepted'
        FROM stock_picking_type spt
        JOIN loc_wh src_wh ON src_wh.id = sp.location_id
        JOIN loc_wh dst_wh ON dst_wh.id = sp.location_dest_id
        WHERE spt.id = sp.picking_type_id
          AND spt.code = 'internal'
          AND sp.state = 'done'
          AND sp.wh_send_state = 'na'
          AND src_wh.warehouse_id IS NOT NULL
          AND dst_wh.warehouse_id IS NOT NULL
          AND src_wh.warehouse_id != dst_wh.warehouse_id;
    """)