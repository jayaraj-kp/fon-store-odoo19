# -*- coding: utf-8 -*-
# Migration: 19.0.1.0.0 → 19.0.2.0.0
# Initialises wh_send_state on existing stock.picking records.
#
# NOTE: picking_type_code is a computed ORM field — it does NOT exist as a
# real DB column. The actual column lives in stock_picking_type.code.
# We join stock_picking_type to filter internal transfers.

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

    # 3. Mark active cross-WH internal transfers as 'pending'
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'pending'
        FROM stock_picking_type spt
        WHERE spt.id = sp.picking_type_id
          AND spt.code = 'internal'
          AND sp.state IN ('confirmed', 'assigned')
          AND sp.wh_send_state = 'na'
          AND EXISTS (
              SELECT 1 FROM stock_location src_loc
              WHERE src_loc.id = sp.location_id
                AND src_loc.warehouse_id IS NOT NULL
          )
          AND EXISTS (
              SELECT 1 FROM stock_location dst_loc
              WHERE dst_loc.id = sp.location_dest_id
                AND dst_loc.warehouse_id IS NOT NULL
          )
          AND (
              SELECT src_loc.warehouse_id FROM stock_location src_loc
              WHERE src_loc.id = sp.location_id
          ) != (
              SELECT dst_loc.warehouse_id FROM stock_location dst_loc
              WHERE dst_loc.id = sp.location_dest_id
          );
    """)

    # 4. Mark already-validated cross-WH internal transfers as 'accepted'
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'accepted'
        FROM stock_picking_type spt
        WHERE spt.id = sp.picking_type_id
          AND spt.code = 'internal'
          AND sp.state = 'done'
          AND sp.wh_send_state = 'na'
          AND EXISTS (
              SELECT 1 FROM stock_location src_loc
              WHERE src_loc.id = sp.location_id
                AND src_loc.warehouse_id IS NOT NULL
          )
          AND EXISTS (
              SELECT 1 FROM stock_location dst_loc
              WHERE dst_loc.id = sp.location_dest_id
                AND dst_loc.warehouse_id IS NOT NULL
          )
          AND (
              SELECT src_loc.warehouse_id FROM stock_location src_loc
              WHERE src_loc.id = sp.location_id
          ) != (
              SELECT dst_loc.warehouse_id FROM stock_location dst_loc
              WHERE dst_loc.id = sp.location_dest_id
          );
    """)