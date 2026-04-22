def post_init_hook(env):
    """Set date format to dd/mm/yyyy for all installed languages."""
    langs = env['res.lang'].search([])
    langs.write({'date_format': '%d/%m/%Y'})
