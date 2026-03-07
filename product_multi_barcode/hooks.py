# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Remove NOT NULL constraint on default_code at DB level."""
    cr = env.cr
    cr.execute("""
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'product_template'
          AND column_name = 'default_code'
    """)
    row = cr.fetchone()
    if row and row[0] == 'NO':
        _logger.info("product_multi_barcode: removing NOT NULL on default_code")
        cr.execute("""
            ALTER TABLE product_template
            ALTER COLUMN default_code DROP NOT NULL
        """)
