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

    # Set 'pending' for existing cross-WH transfers that are still active
    # (state confirmed/assigned, not done/cancel)
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'pending'
        FROM stock_location src_loc
        JOIN stock_warehouse src_wh ON src_wh.id = src_loc.warehouse_id
        JOIN stock_location dst_loc ON dst_loc.id = sp.location_dest_id
        JOIN stock_warehouse dst_wh ON dst_wh.id = dst_loc.warehouse_id
        WHERE sp.location_id = src_loc.id
          AND sp.state IN ('confirmed', 'assigned')
          AND sp.picking_type_code = 'internal'
          AND src_wh.id != dst_wh.id
          AND sp.wh_send_state = 'na';
    """)

    # Set 'accepted' for already-validated cross-WH transfers (historical)
    cr.execute("""
        UPDATE stock_picking sp
        SET wh_send_state = 'accepted'
        FROM stock_location src_loc
        JOIN stock_warehouse src_wh ON src_wh.id = src_loc.warehouse_id
        JOIN stock_location dst_loc ON dst_loc.id = sp.location_dest_id
        JOIN stock_warehouse dst_wh ON dst_wh.id = dst_loc.warehouse_id
        WHERE sp.location_id = src_loc.id
          AND sp.state = 'done'
          AND sp.picking_type_code = 'internal'
          AND src_wh.id != dst_wh.id
          AND sp.wh_send_state = 'na';
    """)
