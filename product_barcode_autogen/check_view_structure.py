#!/usr/bin/env python3
"""
=======================================================
DIAGNOSTIC SCRIPT - Run this on your Odoo 19 server
=======================================================
Purpose: Find what fields/elements exist in the base
         product.template form view so we can write
         a correct xpath for our custom module.

Usage:
  sudo -u odoo python3 check_view_structure.py

Or via psql directly:
  SELECT arch_db FROM ir_ui_view
  WHERE model='product.template'
    AND type='form'
    AND inherit_id IS NULL
  LIMIT 1;
=======================================================
"""
import subprocess, sys

print("""
Run this SQL query in your Odoo database (psql):

  \\c <your_db_name>

  SELECT id, name, arch_db
  FROM ir_ui_view
  WHERE model = 'product.template'
    AND type = 'form'
    AND inherit_id IS NULL
  ORDER BY id
  LIMIT 3;

This will show you exactly what elements are in the
base product template form view so you can verify
the xpath anchors.

If you see a field named 'name', 'type', or 'categ_id'
in the output, the module will work with the current fix.
""")
