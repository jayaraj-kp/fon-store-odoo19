from . import models


def post_init_hook(env):
    """
    Create paperformat and assign to report after module install.
    This avoids XML ref errors for paperformats that may not exist.
    """
    # Create or find our paperformat
    PaperFormat = env['report.paperformat']
    existing = PaperFormat.search([('name', '=', 'FON Label 50x25mm')], limit=1)
    if not existing:
        pf = PaperFormat.create({
            'name': 'FON Label 50x25mm',
            'format': 'custom',
            'page_width': 50,
            'page_height': 25,
            'orientation': 'Portrait',
            'dpi': 203,
        })
    else:
        pf = existing

    # Assign to our report action
    report = env['ir.actions.report'].search([
        ('report_name', '=', 'custom_product_label.report_fon_label')
    ], limit=1)
    if report:
        report.paperformat_id = pf.id


def uninstall_hook(env):
    env['report.paperformat'].search([('name', '=', 'FON Label 50x25mm')]).unlink()
