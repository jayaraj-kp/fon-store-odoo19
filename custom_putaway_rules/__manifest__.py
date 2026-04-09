{
    'name': 'Putaway Rules - All Locations Display',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Warehouse',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'website': 'https://yourcompany.com',

    'depends': [
        'stock',  # Core dependency - putaway rules are in stock module
    ],

    'data': [
        'views/stock_putaway_rule_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,

    'summary': '''
        Modifies putaway rules to display all warehouse locations
        in the "When product arrives in" field, not just parent locations.

        This allows flexibility to put products in sub-locations directly
        from putaway rules without being restricted to parent locations only.
    ''',

    'description': '''
        CHANGES MADE:
        =============
        - Modified: stock.putaway.rule form view
        - Field: location_in_id ("When product arrives in")
        - Change: Removed restriction to parent locations only
        - Original domain: [('company_id', 'in', [company_id] + [False])] + 
                          ([('child_ids', '!=', False)]) or [('company_id', '=', False)]
        - New domain: [('company_id', 'in', [company_id, False])]

        IMPACT:
        =======
        - Users can now select any location (including sub-locations)
        - More flexible warehouse management
        - No data loss or corruption
        - Backward compatible with existing rules

        TESTED WITH:
        ============
        - Odoo 19.0
        - Python 3.10+
    ''',
}