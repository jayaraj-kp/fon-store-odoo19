# -*- coding: utf-8 -*-
from odoo import models, api


class IrUiMenu(models.Model):
    """
    Override menu visibility based on user restrictions.
    This is the most reliable way to hide menus in Odoo 19 —
    it works at the server level, not just DOM level.
    """
    _inherit = 'ir.ui.menu'

    # Map: menu complete_name substring (lowercase) → user restriction field
    MENU_RESTRICTION_MAP = [
        # Inventory
        ('scrap',                       'restrict_scrap_menu'),
        ('physical inventory',          'restrict_physical_inventory'),
        ('inventory adjustments',       'restrict_physical_inventory'),
        ('replenishment',               'restrict_replenishment'),
        ('inventory valuation',         'restrict_inventory_valuation'),
        ('landed costs',                'restrict_landed_costs'),
        # Accounting Reports
        ('balance sheet',               'restrict_balance_sheet'),
        ('profit and loss',             'restrict_profit_loss'),
        ('partner ledger',              'restrict_partner_ledger'),
        ('general ledger',              'restrict_general_ledger'),
        ('trial balance',               'restrict_trial_balance'),
        ('cash flow',                   'restrict_cash_flow'),
        ('aged receivable',             'restrict_aged_receivable'),
        ('aged payable',                'restrict_aged_payable'),
        ('tax report',                  'restrict_tax_report'),
        ('executive summary',           'restrict_executive_summary'),
    ]

    @api.model
    def _visible_menu_ids(self, debug=False):
        """
        Override to filter out restricted menus for the current user.
        This is called by Odoo every time the menu is loaded.
        """
        menu_ids = super()._visible_menu_ids(debug=debug)
        user = self.env.user

        # Skip filtering for superuser / admin
        if user._is_superuser():
            return menu_ids

        # Check if any restriction is active on this user
        active_restrictions = {
            field: True
            for _, field in self.MENU_RESTRICTION_MAP
            if getattr(user, field, False)
        }

        if not active_restrictions:
            return menu_ids

        # Filter menus
        visible_menus = self.browse(menu_ids)
        hidden_ids = set()

        for menu in visible_menus:
            full_name = (menu.complete_name or menu.name or '').lower()
            for keyword, field in self.MENU_RESTRICTION_MAP:
                if active_restrictions.get(field) and keyword in full_name:
                    hidden_ids.add(menu.id)
                    break

        return [mid for mid in menu_ids if mid not in hidden_ids]
