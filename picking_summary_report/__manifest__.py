{
    'name': 'Picking Summary Report',
    'version': '1.0.0',
    'category': 'Inventory',
    'summary': 'Print a grouped picking summary PDF for internal transfers',
    'description': """
        Adds a 'Picking Summary' print option on Internal Transfers.
        Groups products by category and shows Sl No, Category, Location,
        Product, Quantity and Destination — matching the FON-STORE format.
    """,
    'author': 'FON-STORE',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'report/picking_summary_report.xml',
        'report/picking_summary_template.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
