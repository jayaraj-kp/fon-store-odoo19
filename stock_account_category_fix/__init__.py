from . import models


def post_init_hook(env):
    """
    After module install, populate stock account properties for all existing
    product categories that use 'real_time' (Perpetual) valuation but are
    missing the stock account fields.
    """
    import logging
    _logger = logging.getLogger(__name__)

    categories = env['product.category'].search([
        ('property_valuation', '=', 'real_time'),
    ])

    input_account = env['account.account'].search(
        [('name', '=', 'Stock Interim (Received) A/C')], limit=1
    ) or env['account.account'].search(
        [('name', 'ilike', 'Interim (Received)')], limit=1
    )

    output_account = env['account.account'].search(
        [('name', '=', 'Stock Interim (Deliverd) A/C')], limit=1
    ) or env['account.account'].search(
        [('name', 'ilike', 'Interim (Deliver')], limit=1
    )

    valuation_account = env['account.account'].search(
        [('name', 'ilike', 'Stock Valuation')], limit=1
    )

    stock_journal = env['account.journal'].search(
        [('name', 'ilike', 'Inventory')], limit=1
    )

    for cat in categories:
        if input_account and not cat.property_stock_account_input_categ_id:
            cat.property_stock_account_input_categ_id = input_account
            _logger.info("Set Stock Input Account on category '%s'", cat.name)
        if output_account and not cat.property_stock_account_output_categ_id:
            cat.property_stock_account_output_categ_id = output_account
            _logger.info("Set Stock Output Account on category '%s'", cat.name)
        if valuation_account and not cat.property_stock_valuation_account_id:
            cat.property_stock_valuation_account_id = valuation_account
            _logger.info("Set Stock Valuation Account on category '%s'", cat.name)
        if stock_journal and not cat.property_stock_journal:
            cat.property_stock_journal = stock_journal
            _logger.info("Set Stock Journal on category '%s'", cat.name)
