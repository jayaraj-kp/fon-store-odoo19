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
    #
    # NOTE: Before matching, the menu name is normalized:
    #   - " & " → " and "   (handles OCA menus like "Profit & Loss (BAK)")
    #   - text inside parentheses is stripped, e.g. "(BAK)" → ""
    # So keywords here should always use "and" — not "&".
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

    @staticmethod
    def _normalize_menu_name(name):
        """
        Normalize a menu label for consistent keyword matching.

        Fixes:
          - OCA/third-party menus use "&" instead of "and"
            e.g. "Profit & Loss (BAK)" → "profit and loss bak"
          - Suffixes like "(BAK)", "(OCA)" etc. are stripped so the
            base keyword still matches.
        """
        import re
        text = (name or '').lower()
        # Replace " & " with " and "
        text = text.replace(' & ', ' and ')
        # Strip content inside parentheses (e.g. "(BAK)", "(OCA)")
        text = re.sub(r'\(.*?\)', '', text)
        # Collapse extra whitespace
        text = ' '.join(text.split())
        return text

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

        # Build a set of active restriction field names
        active_restrictions = {
            field
            for _, field in self.MENU_RESTRICTION_MAP
            if getattr(user, field, False)
        }

        if not active_restrictions:
            return menu_ids

        # Filter menus
        visible_menus = self.browse(menu_ids)
        hidden_ids = set()

        for menu in visible_menus:
            raw_name = menu.complete_name or menu.name or ''
            normalized = self._normalize_menu_name(raw_name)

            for keyword, field in self.MENU_RESTRICTION_MAP:
                if field in active_restrictions and keyword in normalized:
                    hidden_ids.add(menu.id)
                    break

        return [mid for mid in menu_ids if mid not in hidden_ids]