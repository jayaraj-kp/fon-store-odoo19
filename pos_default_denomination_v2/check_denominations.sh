#!/bin/bash
# ============================================================
# DEBUG SCRIPT: Check pos.bill denomination values in Odoo DB
# Run this on your Odoo server to verify what's stored
# ============================================================
# Usage:
#   chmod +x check_denominations.sh
#   ./check_denominations.sh
#
# OR run the SQL directly in your PostgreSQL client
# ============================================================

DB_NAME="your_odoo_db"   # <-- CHANGE THIS to your actual DB name
DB_USER="odoo"            # <-- CHANGE THIS to your PostgreSQL user

echo "======================================"
echo " POS Denomination Debug Check"
echo "======================================"
echo ""
echo "1. All current pos.bill values in database:"
echo "----------------------------------------------"
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT id, value
FROM pos_bill
ORDER BY value DESC;
"

echo ""
echo "2. Checking if correct INR denominations exist (500,200,100,50,20,10,5,2,1):"
echo "------------------------------------------------------------------------------"
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
    val AS expected_value,
    CASE WHEN EXISTS (SELECT 1 FROM pos_bill WHERE value = val)
         THEN '✅ EXISTS'
         ELSE '❌ MISSING'
    END AS status
FROM unnest(ARRAY[500,200,100,50,20,10,5,2,1]::numeric[]) AS val
ORDER BY val DESC;
"

echo ""
echo "3. Wrong/unexpected denomination values (if any):"
echo "---------------------------------------------------"
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT id, value AS wrong_value
FROM pos_bill
WHERE value NOT IN (500, 200, 100, 50, 20, 10, 5, 2, 1)
ORDER BY value DESC;
"

echo ""
echo "======================================"
echo " Fix Commands (run if needed)"
echo "======================================"
echo ""
echo "-- DELETE all wrong values:"
echo "DELETE FROM pos_bill WHERE value NOT IN (500, 200, 100, 50, 20, 10, 5, 2, 1);"
echo ""
echo "-- INSERT correct values if missing:"
echo "INSERT INTO pos_bill (value) SELECT val FROM unnest(ARRAY[500,200,100,50,20,10,5,2,1]::numeric[]) AS val WHERE val NOT IN (SELECT value FROM pos_bill);"
echo ""
echo "======================================"
