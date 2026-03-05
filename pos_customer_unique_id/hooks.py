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

# The content block to inject – reused across different xpath wrappers
_CONTENT = """
            <group string="Customer ID Settings" colspan="2" name="customer_uid_group">
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
"""

# Each candidate is (xpath_expr, position).
# We try them in order; the first one that validates against the actual view wins.
_XPATH_CANDIDATES = [
    # Odoo 17/18/19: notebook with tabs
    ('//notebook', 'inside', '<page string="Customer ID" name="customer_uid_page">', '</page>'),
    # Flat form with a sheet > group structure (no notebook)
    ('//sheet', 'inside', '<group string="Customer ID">', '</group>'),
    # Generic: append after last group inside sheet
    ('//sheet//group[last()]', 'after', '', ''),
    # Last resort: just before the closing of the form
    ('//form', 'inside', '<group string="Customer ID">', '</group>'),
]

# External ID we use to track our injected view
_VIEW_XMLID = 'pos_customer_unique_id.view_pos_config_form_customer_uid'


def _find_pos_config_form_view(env):
    """
    Find the primary (non-inherited) form view for pos.config.
    We try known XML IDs first, then fall back to a DB search.
    Also logs ALL pos.config form views found so the admin can check odoo.log.
    """
    IrUiView = env['ir.ui.view']

    # Log ALL form views for pos.config to help diagnose
    all_views = IrUiView.search([('model', '=', 'pos.config'), ('type', '=', 'form')])
    for v in all_views:
        _logger.info(
            'POS Customer UID [DIAG] pos.config form view: id=%s name=%s inherit_id=%s xmlid=%s',
            v.id, v.name, v.inherit_id.id if v.inherit_id else None,
            env['ir.model.data'].search([('model', '=', 'ir.ui.view'), ('res_id', '=', v.id)], limit=1).complete_name or 'no-xmlid'
        )

    # Known XML IDs across Odoo versions – try them in order
    known_refs = [
        'point_of_sale.pos_config_view_form',
        'point_of_sale.view_pos_config_form',
        'point_of_sale.pos_config_form_view',
        'point_of_sale.pos_config_form',
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
        ('inherit_id', '=', False),
        ('active', '=', True),
    ], order='priority asc', limit=1)

    if view:
        _logger.info('POS Customer UID: found POS config form via DB search (id=%s name=%s)', view.id, view.name)
        return view

    _logger.warning('POS Customer UID: could NOT find a primary form view for pos.config!')
    return None


def _build_arch(xpath_expr, position, wrap_open, wrap_close):
    """Build a complete <data> arch string for a given xpath + position."""
    return (
        f'<data>\n'
        f'    <xpath expr="{xpath_expr}" position="{position}">\n'
        f'        {wrap_open}\n'
        f'{_CONTENT}'
        f'        {wrap_close}\n'
        f'    </xpath>\n'
        f'</data>'
    )


def _test_arch(env, parent_view, arch):
    """
    Return True if `arch` is valid when inherited from `parent_view`.
    Uses ir.ui.view._check_xml() / validate_view_arch() – whichever is available.
    """
    IrUiView = env['ir.ui.view']
    try:
        # Build a temporary in-memory view dict and validate
        test_view = IrUiView.new({
            'name': '_test_pos_uid',
            'model': 'pos.config',
            'inherit_id': parent_view.id,
            'arch': arch,
        })
        # Odoo 16+: _check_xml validates the combined arch
        IrUiView._check_xml(test_view)  # raises if invalid
        return True
    except Exception:
        pass

    # Fallback: just try lxml xpath to see if node exists in parent arch
    try:
        from lxml import etree
        import re
        # Extract the xpath expr
        m = re.search(r'expr="([^"]+)"', arch)
        if not m:
            return False
        xpath_expr = m.group(1)
        root = etree.fromstring(parent_view.arch.encode())
        nodes = root.xpath(xpath_expr)
        return bool(nodes)
    except Exception:
        return False


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
            'POS Customer UID: cannot inject settings tab – POS config form view not found.'
        )
        return

    # Log the actual parent view arch so we can diagnose xpath issues
    _logger.info(
        'POS Customer UID: parent view id=%s name=%s arch_preview=%.500s',
        parent_view.id, parent_view.name,
        (parent_view.arch or '')[:500]
    )

    # Try each xpath candidate until one validates
    chosen_arch = None
    for xpath_expr, position, wrap_open, wrap_close in _XPATH_CANDIDATES:
        arch = _build_arch(xpath_expr, position, wrap_open, wrap_close)
        if _test_arch(env, parent_view, arch):
            chosen_arch = arch
            _logger.info('POS Customer UID: using xpath="%s" position="%s"', xpath_expr, position)
            break

    if not chosen_arch:
        # Last-ditch: use a completely standalone (non-inherited) form view
        _logger.warning(
            'POS Customer UID: no xpath matched – creating standalone auxiliary view.'
        )
        chosen_arch = (
            '<form string="POS Customer ID Config">'
            '<sheet><group string="Customer ID Settings" colspan="2">'
            + _CONTENT +
            '</group></sheet></form>'
        )

    # Create the inherited view
    new_view = IrUiView.create({
        'name': 'pos.config.form.customer.uid',
        'model': 'pos.config',
        'inherit_id': parent_view.id,
        'arch': chosen_arch,
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
        'POS Customer UID: successfully injected Customer ID tab '
        '(parent id=%s, new view id=%s)', parent_view.id, new_view.id
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
