# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def post_install_hook(env):
    """
    After module install, clear any saved user preferences that have
    analytic_distribution marked as hidden in sale.order.line list views.

    Odoo stores optional column visibility in ir.ui.view.custom per user.
    We need to remove any records that hide analytic_distribution so it
    shows immediately for all users without needing a manual toggle.
    """
    try:
        # Find all customized views for sale.order.line list
        # where analytic_distribution is stored as hidden
        custom_views = env['ir.ui.view.custom'].search([
            ('user_id', '!=', False),
        ])

        cleaned = 0
        for custom_view in custom_views:
            arch = custom_view.arch
            if 'analytic_distribution' in arch and 'optional="hide"' in arch:
                # Remove this custom view record so the base view takes effect
                custom_view.unlink()
                cleaned += 1

        if cleaned:
            _logger.info(
                "sale_analytic_default: Cleared %d user preference(s) that "
                "had analytic_distribution hidden.", cleaned
            )
        else:
            _logger.info(
                "sale_analytic_default: No user preferences needed clearing."
            )
    except Exception as e:
        _logger.warning(
            "sale_analytic_default: Could not clear user preferences: %s", e
        )
