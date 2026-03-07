# -*- coding: utf-8 -*-
"""
Migration: Remove NOT NULL constraint on product_template.default_code
This is needed for Odoo 19 CE where the column has a DB-level NOT NULL
but the field should be optional.
"""


def migrate(cr, version):
    # Check if the NOT NULL constraint exists
    cr.execute("""
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'product_template'
          AND column_name = 'default_code'
    """)
    row = cr.fetchone()
    if row and row[0] == 'NO':
        # Remove the NOT NULL constraint at DB level
        cr.execute("""
            ALTER TABLE product_template
            ALTER COLUMN default_code DROP NOT NULL
        """)
