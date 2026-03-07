# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _fix_default_code_constraint(env.cr)


def uninstall_hook(env):
    pass


def _fix_default_code_constraint(cr):
    """
    Odoo 19 enforces NOT NULL on default_code at DB level.
    We set a DB-level default so web_save can never insert NULL.
    """
    # 1. Drop NOT NULL if present
    cr.execute("""
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'product_template'
          AND column_name = 'default_code'
    """)
    row = cr.fetchone()
    if row and row[0] == 'NO':
        _logger.info("product_multi_barcode: dropping NOT NULL on default_code")
        cr.execute("""
            ALTER TABLE product_template
            ALTER COLUMN default_code DROP NOT NULL
        """)

    # 2. Add a DB-level default function so if NULL slips through, PG generates one
    cr.execute("""
        CREATE OR REPLACE FUNCTION generate_product_ref()
        RETURNS TEXT AS $$
        DECLARE
            ref TEXT;
        BEGIN
            LOOP
                ref := 'PRD' || LPAD(FLOOR(RANDOM() * 999999)::TEXT, 6, '0');
                EXIT WHEN NOT EXISTS (
                    SELECT 1 FROM product_template WHERE default_code = ref
                );
            END LOOP;
            RETURN ref;
        END;
        $$ LANGUAGE plpgsql;
    """)

    cr.execute("""
        ALTER TABLE product_template
        ALTER COLUMN default_code SET DEFAULT generate_product_ref()
    """)
    _logger.info("product_multi_barcode: DB default set on default_code")
