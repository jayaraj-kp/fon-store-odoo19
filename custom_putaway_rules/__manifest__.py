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

    'data': [],  # No XML files needed - using Python override instead

    'installable': True,
    'application': False,
    'auto_install': False,

    'summary': '''
        Modifies putaway rules to display all warehouse locations
        in the "When product arrives in" field, not just parent locations.
    ''',

    'description': '''
        CUSTOMIZATION DETAILS:

        MODIFIED FIELD:
        - Model: stock.putaway.rule
        - Field: location_in_id
        - Display Name: "When product arrives in"

        ORIGINAL BEHAVIOR:
        - Only showed parent locations (locations with child_ids)
        - Original domain: [('company_id', 'in', [company_id] + [False])] + 
                          ([('child_ids', '!=', False)]) or [('company_id', '=', False)]

        NEW BEHAVIOR:
        - Shows ALL company locations (parent and sub-locations)
        - New domain: [('company_id', 'in', [company_id, False])]

        BENEFITS:
        - More flexibility in warehouse management
        - Can create putaway rules for sub-locations directly
        - Backward compatible with existing rules
        - No data loss or corruption

        IMPLEMENTATION:
        - Uses Python model inheritance (no XML views)
        - More reliable than XML-based approach
        - Works with all Odoo 19 versions

        TESTED WITH:
        - Odoo 19.0 CE
        - Python 3.10+
    ''',
}