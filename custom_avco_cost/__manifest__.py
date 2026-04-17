{
    'name': 'Custom Cost: Total Value ÷ Latest Purchase Price',
    'version': '19.0.1.0.0',
    'summary': 'Auto-updates product cost = Total Stock Value ÷ Latest Purchase Price on every purchase',
    'description': '''
        Custom Costing Method:
        ─────────────────────
        On every confirmed purchase (vendor bill or PO receipt validation):

        Formula:
            New Cost = Total Stock Value ÷ Latest Purchase Unit Price

        Example:
            Old stock  : 50 qty × ₹200 = ₹10,000
            New purchase: 100 qty × ₹250 = ₹25,000
            Total Value : ₹35,000
            Latest Price: ₹250
            New Cost    : ₹35,000 ÷ ₹250 = ₹140

        Works with:
            - Periodic (manual) inventory valuation
            - Perpetual (automatic) inventory valuation
            - Any product category costing method
    ''',
    'author': 'Custom',
    'category': 'Inventory/Inventory',
    'depends': ['purchase', 'stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
