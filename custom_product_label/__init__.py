from . import models


def post_init_hook(env):
    # Clean up any old report actions with old template names
    old_reports = env['ir.actions.report'].search([
        ('report_name', 'in', [
            'custom_product_label.report_product_label_template',
            'custom_product_label.report_fon_label',
        ])
    ])
    # Keep only the one matching our current name, delete stale ones
    current = old_reports.filtered(
        lambda r: r.report_name == 'custom_product_label.report_fon_label'
    )
    (old_reports - current).unlink()

    # Create or find our paperformat
    PaperFormat = env['report.paperformat']
    pf = PaperFormat.search([('name', '=', 'FON Label 50x25mm')], limit=1)
    if not pf:
        pf = PaperFormat.create({
            'name': 'FON Label 50x25mm',
            'format': 'custom',
            'page_width': 50,
            'page_height': 25,
            'orientation': 'Portrait',
            'dpi': 203,
        })

    # Assign paperformat to our report
    report = env['ir.actions.report'].search([
        ('report_name', '=', 'custom_product_label.report_fon_label')
    ], limit=1)
    if report:
        report.paperformat_id = pf.id


def uninstall_hook(env):
    env['report.paperformat'].search([('name', '=', 'FON Label 50x25mm')]).unlink()
