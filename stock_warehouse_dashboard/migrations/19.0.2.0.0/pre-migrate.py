# -*- coding: utf-8 -*-
# Migration: 19.0.1.0.0 → 19.0.2.0.0
# Initialises wh_send_state on existing stock.picking records.

def migrate(cr, version):
    if not version:
        return

    # Set 'na' as default for all existing transfers
    cr.execute("""
        ALTER TABLE stock_picking
        ADD COLUMN IF NOT EXISTS wh_send_state VARCHAR DEFAULT 'na';
    """)

    # Set 'na' as default for all records that have no value yet
    cr.execute("""
        UPDATE stock_picking
        SET wh_send_state = 'na'
        WHERE wh_send_state IS NULL;
    """)

    # Set 'pending' for active cross-WH internal transfers (not yet validated)
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'pending'
        WHERE sp.state IN ('confirmed', 'assigned')
          AND sp.picking_type_code = 'internal'
          AND sp.wh_send_state = 'na'
          AND EXISTS (
              SELECT 1 FROM stock_location src_loc
              JOIN stock_warehouse src_wh ON src_wh.id = src_loc.warehouse_id
              WHERE src_loc.id = sp.location_id
                AND src_loc.warehouse_id IS NOT NULL
          )
          AND EXISTS (
              SELECT 1 FROM stock_location dst_loc
              JOIN stock_warehouse dst_wh ON dst_wh.id = dst_loc.warehouse_id
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

    # Set 'accepted' for already-done cross-WH internal transfers (historical)
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'accepted'
        WHERE sp.state = 'done'
          AND sp.picking_type_code = 'internal'
          AND sp.wh_send_state = 'na'
          AND EXISTS (
              SELECT 1 FROM stock_location src_loc
              JOIN stock_warehouse src_wh ON src_wh.id = src_loc.warehouse_id
              WHERE src_loc.id = sp.location_id
                AND src_loc.warehouse_id IS NOT NULL
          )
          AND EXISTS (
              SELECT 1 FROM stock_location dst_loc
              JOIN stock_warehouse dst_wh ON dst_wh.id = dst_loc.warehouse_id
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
