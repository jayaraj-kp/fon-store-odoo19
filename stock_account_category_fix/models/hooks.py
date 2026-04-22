import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    After module install, set the default ir.property values for
    Stock Input Account and Stock Output Account on product.category
    so that new categories automatically show the correct interim accounts.
    """

    def get_account(xml_id):
        try:
            return env.ref(xml_id)
        except Exception:
            _logger.warning("Could not resolve XML ID: %s", xml_id)
            return None

    # Resolve the two interim accounts
    account_input = get_account('stock_account.stock_account_interim_received')
    account_output = get_account('stock_account.stock_account_interim_delivered')

    fields_to_set = []
    if account_input:
        fields_to_set.append(('property_stock_account_input_categ_id', account_input))
    if account_output:
        fields_to_set.append(('property_stock_account_output_categ_id', account_output))

    if not fields_to_set:
        _logger.warning("Stock interim accounts not found. Skipping default property setup.")
        return

    ProductCategory = env['product.category']

    for field_name, account in fields_to_set:
        field = ProductCategory._fields.get(field_name)
        if not field:
            continue

        # Check if a global default ir.property already exists for this field
        existing = env['ir.property'].sudo().search([
            ('name', '=', field_name),
            ('res_id', '=', False),           # False = global default (not per-record)
            ('fields_id.model', '=', 'product.category'),
        ], limit=1)

        value = f'account.account,{account.id}'

        if existing:
            existing.sudo().write({'value_reference': value})
            _logger.info("Updated default ir.property for %s -> %s", field_name, account.display_name)
        else:
            fields_id = env['ir.model.fields'].sudo().search([
                ('name', '=', field_name),
                ('model', '=', 'product.category'),
            ], limit=1)

            if fields_id:
                env['ir.property'].sudo().create({
                    'name': field_name,
                    'fields_id': fields_id.id,
                    'res_id': False,            # Global default
                    'value_reference': value,
                    'type': 'many2one',
                })
                _logger.info(
                    "Created default ir.property for %s -> %s",
                    field_name, account.display_name
                )