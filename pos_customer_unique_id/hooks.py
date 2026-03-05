# -*- coding: utf-8 -*-
"""
post_init_hook / uninstall_hook

Because Odoo 19 CE may have a different internal XML ID for the POS config
form view (it has changed across versions), we do NOT rely on a hard-coded
ref="point_of_sale.xxx" in XML.  Instead we locate the correct primary view
at install time and create the inherited view programmatically.
"""
import logging

_logger = logging.getLogger(__name__)

# The arch we want to inject into the POS config form view
_ARCH = """
<data>
    <xpath expr="//notebook" position="inside">
        <page string="Customer ID" name="customer_uid_page">

            <group string="Shop Customer ID Settings" colspan="2">
                <group>
                    <field name="shop_code" placeholder="e.g. CHL, KON, TVM …"/>
                </group>
                <group>
                    <field name="customer_sequence_id" readonly="1"/>
                </group>
            </group>

            <div class="alert alert-info" role="alert" style="margin:8px 0;">
                <strong>How it works: </strong>
                Enter a short prefix code for this shop (e.g.
                <b>CHL</b> for Chelari, <b>KON</b> for Kondotty).
                When a new customer is created from this POS terminal they will
                automatically receive a unique ID like
                <b>CHL - 00001</b>, <b>CHL - 00002</b>, etc.
            </div>

            <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
                <button name="action_setup_customer_sequence"
                        type="object"
                        string="Setup / Update Sequence"
                        class="btn btn-primary"
                        invisible="not shop_code"/>
                <button name="action_reset_customer_sequence"
                        type="object"
                        string="Reset Counter to 1"
                        class="btn btn-warning"
                        invisible="not customer_sequence_id"
                        confirm="This will reset the customer ID counter to 1. Existing IDs will NOT change. Continue?"/>
                <button name="action_view_shop_customers"
                        type="object"
                        string="View Shop Customers"
                        class="btn btn-secondary"
                        invisible="not id"/>
            </div>

            <group string="Statistics" invisible="not id">
                <field name="customer_id_count"
                       string="Total Customers Created from this Shop"
                       readonly="1"/>
            </group>

        </page>
    </xpath>
</data>
"""

# External ID we use to track our injected view
_VIEW_XMLID = 'pos_customer_unique_id.view_pos_config_form_customer_uid'


def _find_pos_config_form_view(env):
    """
    Find the primary (non-inherited) form view for pos.config.
    We try known XML IDs first, then fall back to a DB search.
    """
    IrUiView = env['ir.ui.view']

    # Known XML IDs across Odoo versions – try them in order
    known_refs = [
        'point_of_sale.pos_config_view_form',
        'point_of_sale.view_pos_config_form',
        'point_of_sale.pos_config_form_view',
    ]
    for ref in known_refs:
        try:
            view = env.ref(ref, raise_if_not_found=False)
            if view:
                _logger.info('POS Customer UID: found POS config form via %s', ref)
                return view
        except Exception:
            pass

    # Final fallback: search DB for the primary form view for pos.config
    view = IrUiView.search([
        ('model', '=', 'pos.config'),
        ('type', '=', 'form'),
        ('inherit_id', '=', False),   # primary view only
        ('active', '=', True),
    ], order='priority asc', limit=1)

    if view:
        _logger.info('POS Customer UID: found POS config form via DB search (id=%s)', view.id)
        return view

    _logger.warning('POS Customer UID: could NOT find a primary form view for pos.config!')
    return None


def post_init_hook(env):
    """Called once after the module is installed."""
    IrUiView = env['ir.ui.view']
    IrModelData = env['ir.model.data']

    # Avoid creating duplicates on repeated installs/upgrades
    existing = IrModelData.search([
        ('module', '=', 'pos_customer_unique_id'),
        ('name', '=', 'view_pos_config_form_customer_uid'),
    ])
    if existing:
        _logger.info('POS Customer UID: inherited view already exists, skipping creation.')
        return

    parent_view = _find_pos_config_form_view(env)
    if not parent_view:
        _logger.error(
            'POS Customer UID: cannot inject settings tab – POS config form view not found. '
            'You can still use the module; shop codes can be set via the partner backend form.'
        )
        return

    # Create the inherited view
    new_view = IrUiView.create({
        'name': 'pos.config.form.customer.uid',
        'model': 'pos.config',
        'inherit_id': parent_view.id,
        'arch': _ARCH,
        'active': True,
        'priority': 99,
    })

    # Register an ir.model.data entry so Odoo tracks it properly
    IrModelData.create({
        'module': 'pos_customer_unique_id',
        'name': 'view_pos_config_form_customer_uid',
        'model': 'ir.ui.view',
        'res_id': new_view.id,
        'noupdate': False,
    })

    _logger.info(
        'POS Customer UID: successfully injected Customer ID tab into pos.config '
        'form view (parent id=%s, new view id=%s)', parent_view.id, new_view.id
    )


def uninstall_hook(env):
    """Remove our injected view when the module is uninstalled."""
    IrModelData = env['ir.model.data']
    record = IrModelData.search([
        ('module', '=', 'pos_customer_unique_id'),
        ('name', '=', 'view_pos_config_form_customer_uid'),
        ('model', '=', 'ir.ui.view'),
    ])
    if record:
        view = env['ir.ui.view'].browse(record.res_id)
        view.unlink()
        record.unlink()
        _logger.info('POS Customer UID: removed injected pos.config form view tab.')
