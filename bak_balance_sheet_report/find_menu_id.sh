#!/bin/bash
# Run this on your Odoo server to find the correct Reporting menu XML ID
# Usage: bash find_menu_id.sh <database_name>

DB=${1:-odoo}
echo "Searching for accounting report menu IDs in database: $DB"
echo ""
psql -U odoo "$DB" -c "
SELECT module || '.' || name AS xmlid
FROM ir_model_data
WHERE model = 'ir.ui.menu'
  AND (
    (module ILIKE '%account%' AND name ILIKE '%report%')
    OR name ILIKE '%finance_report%'
  )
ORDER BY module, name;
"
