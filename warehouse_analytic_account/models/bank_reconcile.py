# # # -*- coding: utf-8 -*-
# # import logging
# # from odoo import api, models
# #
# # _logger = logging.getLogger(__name__)
# #
# # _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
# #
# #
# # def _get_user_warehouse(user):
# #     for fname in _WAREHOUSE_FIELDS:
# #         if fname in user._fields:
# #             return getattr(user, fname, False)
# #     return False
# #
# #
# # def _resolve_analytic_for_statement_line(st_line):
# #     """
# #     Resolve the correct analytic account for a bank statement line.
# #
# #     Priority order:
# #     1. Warehouse linked to the journal of the statement line
# #        (most reliable — the journal belongs to CHELARI-SHOP cash journal)
# #     2. Warehouse linked to the POS config that created this statement line
# #        (via session → config → picking_type → warehouse)
# #     3. Default warehouse of the current user
# #        (fallback for manually created statement lines)
# #
# #     Returns an analytic account record or False.
# #     """
# #     # --- Priority 1: Journal → Warehouse → Analytic ---
# #     journal = getattr(st_line, 'journal_id', False)
# #     if journal:
# #         # Try direct warehouse on journal
# #         wh = getattr(journal, 'warehouse_id', False)
# #         if wh and getattr(wh, 'analytic_account_id', False):
# #             _logger.debug('Analytic resolved from journal warehouse: %s', wh.name)
# #             return wh.analytic_account_id
# #
# #         # Try via the journal's default account → company warehouse mapping
# #         # Many POS cash journals are named per shop (e.g. "Cash CHLR")
# #         # so we check all warehouses and match by journal
# #         warehouses = st_line.env['stock.warehouse'].search([
# #             ('analytic_account_id', '!=', False),
# #             ('company_id', '=', st_line.company_id.id),
# #         ])
# #         for wh in warehouses:
# #             # Check if this warehouse has POS configs using this journal
# #             pos_configs = st_line.env['pos.config'].search([
# #                 ('company_id', '=', st_line.company_id.id),
# #             ])
# #             for config in pos_configs:
# #                 config_wh = False
# #                 picking_type = getattr(config, 'picking_type_id', False)
# #                 if picking_type:
# #                     config_wh = getattr(picking_type, 'warehouse_id', False)
# #                 if not config_wh:
# #                     config_wh = getattr(config, 'warehouse_id', False)
# #
# #                 if config_wh and config_wh.id == wh.id:
# #                     # Check if any payment method of this config uses this journal
# #                     for pm in getattr(config, 'payment_method_ids', []):
# #                         pm_journal = getattr(pm, 'journal_id', False)
# #                         if pm_journal and pm_journal.id == journal.id:
# #                             _logger.debug(
# #                                 'Analytic resolved from POS config %s journal match: %s',
# #                                 config.name, wh.name
# #                             )
# #                             return wh.analytic_account_id
# #
# #     # --- Priority 2: POS session linked to this statement line ---
# #     # account.bank.statement.line may have a pos_session_id in some versions
# #     session = getattr(st_line, 'pos_session_id', False)
# #     if session:
# #         config = getattr(session, 'config_id', False)
# #         if config:
# #             picking_type = getattr(config, 'picking_type_id', False)
# #             if picking_type:
# #                 wh = getattr(picking_type, 'warehouse_id', False)
# #                 if wh and getattr(wh, 'analytic_account_id', False):
# #                     _logger.debug(
# #                         'Analytic resolved from POS session: %s', wh.name
# #                     )
# #                     return wh.analytic_account_id
# #
# #     # --- Priority 3: Current user's default warehouse ---
# #     user = st_line.env.user
# #     wh = _get_user_warehouse(user)
# #     if wh and getattr(wh, 'analytic_account_id', False):
# #         _logger.debug('Analytic resolved from user warehouse: %s', wh.name)
# #         return wh.analytic_account_id
# #
# #     return False
# #
# #
# # def _inject_analytic_into_data(data, analytic):
# #     """
# #     Inject the warehouse analytic into every line of the reconcile
# #     data list that does not already have one.
# #     """
# #     if not data or not analytic:
# #         return data
# #     key = str(analytic.id)
# #     for line in data:
# #         existing = line.get('analytic_distribution') or {}
# #         if key not in existing:
# #             new_dist = dict(existing)
# #             new_dist[key] = 100.0
# #             line['analytic_distribution'] = new_dist
# #     return data
# #
# #
# # def _inject_analytic_into_reconcile_info(reconcile_info, analytic):
# #     if not reconcile_info or not analytic:
# #         return reconcile_info
# #     _inject_analytic_into_data(reconcile_info.get('data', []), analytic)
# #     return reconcile_info
# #
# #
# # class AccountBankStatementLine(models.Model):
# #     _inherit = 'account.bank.statement.line'
# #
# #     def _default_reconcile_data(self, from_unreconcile=False):
# #         result = super()._default_reconcile_data(from_unreconcile=from_unreconcile)
# #         analytic = _resolve_analytic_for_statement_line(self)
# #         if analytic:
# #             _inject_analytic_into_reconcile_info(result, analytic)
# #         return result
# #
# #     def _recompute_suspense_line(self, data, reconcile_auxiliary_id,
# #                                  manual_reference):
# #         result = super()._recompute_suspense_line(
# #             data, reconcile_auxiliary_id, manual_reference
# #         )
# #         analytic = _resolve_analytic_for_statement_line(self)
# #         if analytic:
# #             _inject_analytic_into_reconcile_info(result, analytic)
# #         return result
# #
# #     def _reconcile_data_by_model(self, data, reconcile_model,
# #                                  reconcile_auxiliary_id):
# #         new_data, new_id = super()._reconcile_data_by_model(
# #             data, reconcile_model, reconcile_auxiliary_id
# #         )
# #         analytic = _resolve_analytic_for_statement_line(self)
# #         if analytic:
# #             _inject_analytic_into_data(new_data, analytic)
# #         return new_data, new_id
# #
# #     def _get_reconcile_line(self, line, kind, is_counterpart=False,
# #                             max_amount=False, from_unreconcile=False,
# #                             reconcile_auxiliary_id=False, move=False,
# #                             is_reconciled=False):
# #         reconcile_auxiliary_id, lines = super()._get_reconcile_line(
# #             line, kind,
# #             is_counterpart=is_counterpart,
# #             max_amount=max_amount,
# #             from_unreconcile=from_unreconcile,
# #             reconcile_auxiliary_id=reconcile_auxiliary_id,
# #             move=move,
# #             is_reconciled=is_reconciled,
# #         )
# #         analytic = _resolve_analytic_for_statement_line(self)
# #         if analytic:
# #             _inject_analytic_into_data(lines, analytic)
# #         return reconcile_auxiliary_id, lines
# #
# #     def reconcile_bank_line(self):
# #         result = super().reconcile_bank_line()
# #         key_map = {}
# #         for st_line in self:
# #             analytic = _resolve_analytic_for_statement_line(st_line)
# #             if not analytic or not st_line.move_id:
# #                 continue
# #             key = str(analytic.id)
# #             for line in st_line.move_id.line_ids.filtered(lambda l: l.account_id):
# #                 existing = line.analytic_distribution or {}
# #                 if key not in existing:
# #                     new_dist = dict(existing)
# #                     new_dist[key] = 100.0
# #                     try:
# #                         line.analytic_distribution = new_dist
# #                     except Exception as e:
# #                         _logger.warning(
# #                             'Could not set analytic on reconcile line %s: %s',
# #                             line.id, e
# #                         )
# #         return result
#
# # -*- coding: utf-8 -*-
# import logging
# from odoo import api, models
#
# _logger = logging.getLogger(__name__)
#
# _WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')
#
#
# def _get_user_warehouse(user):
#     for fname in _WAREHOUSE_FIELDS:
#         if fname in user._fields:
#             return getattr(user, fname, False)
#     return False
#
#
# def _resolve_analytic_for_statement_line(st_line):
#     """
#     Resolve the correct analytic account for a bank statement line.
#
#     Priority order:
#     1. Warehouse linked to the journal of the statement line
#        (most reliable — the journal belongs to CHELARI-SHOP cash journal)
#     2. Warehouse linked to the POS config that created this statement line
#        (via session → config → picking_type → warehouse)
#     3. Default warehouse of the current user
#        (fallback for manually created statement lines)
#
#     Returns an analytic account record or False.
#     """
#     # --- Priority 1: Journal → Warehouse → Analytic ---
#     journal = getattr(st_line, 'journal_id', False)
#     if journal:
#         # Try direct warehouse on journal
#         wh = getattr(journal, 'warehouse_id', False)
#         if wh and getattr(wh, 'analytic_account_id', False):
#             _logger.debug('Analytic resolved from journal warehouse: %s', wh.name)
#             return wh.analytic_account_id
#
#         # Match journal to a POS config's payment method to find warehouse
#         warehouses = st_line.env['stock.warehouse'].search([
#             ('analytic_account_id', '!=', False),
#             ('company_id', '=', st_line.company_id.id),
#         ])
#         for wh in warehouses:
#             pos_configs = st_line.env['pos.config'].search([
#                 ('company_id', '=', st_line.company_id.id),
#             ])
#             for config in pos_configs:
#                 config_wh = False
#                 picking_type = getattr(config, 'picking_type_id', False)
#                 if picking_type:
#                     config_wh = getattr(picking_type, 'warehouse_id', False)
#                 if not config_wh:
#                     config_wh = getattr(config, 'warehouse_id', False)
#
#                 if config_wh and config_wh.id == wh.id:
#                     for pm in getattr(config, 'payment_method_ids', []):
#                         pm_journal = getattr(pm, 'journal_id', False)
#                         if pm_journal and pm_journal.id == journal.id:
#                             _logger.debug(
#                                 'Analytic resolved from POS config %s journal match: %s',
#                                 config.name, wh.name
#                             )
#                             return wh.analytic_account_id
#
#     # --- Priority 2: POS session linked to this statement line ---
#     session = getattr(st_line, 'pos_session_id', False)
#     if session:
#         config = getattr(session, 'config_id', False)
#         if config:
#             picking_type = getattr(config, 'picking_type_id', False)
#             if picking_type:
#                 wh = getattr(picking_type, 'warehouse_id', False)
#                 if wh and getattr(wh, 'analytic_account_id', False):
#                     _logger.debug(
#                         'Analytic resolved from POS session: %s', wh.name
#                     )
#                     return wh.analytic_account_id
#
#     # --- Priority 3: Current user's default warehouse ---
#     user = st_line.env.user
#     wh = _get_user_warehouse(user)
#     if wh and getattr(wh, 'analytic_account_id', False):
#         _logger.debug('Analytic resolved from user warehouse: %s', wh.name)
#         return wh.analytic_account_id
#
#     return False
#
#
# def _inject_analytic_into_data(data, analytic):
#     """
#     Inject the warehouse analytic into every line of the reconcile
#     data list that does not already have one.
#     """
#     if not data or not analytic:
#         return data
#     key = str(analytic.id)
#     for line in data:
#         existing = line.get('analytic_distribution') or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             line['analytic_distribution'] = new_dist
#     return data
#
#
# def _inject_analytic_into_reconcile_info(reconcile_info, analytic):
#     if not reconcile_info or not analytic:
#         return reconcile_info
#     _inject_analytic_into_data(reconcile_info.get('data', []), analytic)
#     return reconcile_info
#
#
# def _stamp_analytic_on_move(move, analytic):
#     """
#     Directly write analytic_distribution on all account.move.line records
#     of a posted move using sudo() to bypass lock.
#     This covers the CRDCH/ and CSCHL/ journal entries created by POS payments.
#     """
#     if not move or not analytic:
#         return
#     key = str(analytic.id)
#     for line in move.line_ids.filtered(lambda l: l.account_id):
#         existing = line.analytic_distribution or {}
#         if key not in existing:
#             new_dist = dict(existing)
#             new_dist[key] = 100.0
#             try:
#                 line.sudo().with_context(
#                     check_move_validity=False,
#                     skip_account_move_synchronization=True,
#                 ).analytic_distribution = new_dist
#                 _logger.debug(
#                     'Bank stmt analytic %s applied to move %s line %s (%s)',
#                     analytic.name, move.name, line.id, line.account_id.code,
#                 )
#             except Exception as e:
#                 _logger.warning(
#                     'Could not set analytic on move %s line %s: %s',
#                     move.name, line.id, e,
#                 )
#
#
# class AccountBankStatementLine(models.Model):
#     _inherit = 'account.bank.statement.line'
#
#     @api.model_create_multi
#     def create(self, vals_list):
#         """
#         Stamp analytic on the statement line's own move (CRDCH/, CSCHL/ etc.)
#         immediately at creation — before session closing or reconciliation.
#         This ensures Card/Cash payment journal entries always get the analytic.
#         """
#         st_lines = super().create(vals_list)
#         for st_line in st_lines:
#             analytic = _resolve_analytic_for_statement_line(st_line)
#             if analytic and st_line.move_id:
#                 _stamp_analytic_on_move(st_line.move_id, analytic)
#         return st_lines
#
#     def _default_reconcile_data(self, from_unreconcile=False):
#         result = super()._default_reconcile_data(from_unreconcile=from_unreconcile)
#         analytic = _resolve_analytic_for_statement_line(self)
#         if analytic:
#             _inject_analytic_into_reconcile_info(result, analytic)
#         return result
#
#     def _recompute_suspense_line(self, data, reconcile_auxiliary_id,
#                                  manual_reference):
#         result = super()._recompute_suspense_line(
#             data, reconcile_auxiliary_id, manual_reference
#         )
#         analytic = _resolve_analytic_for_statement_line(self)
#         if analytic:
#             _inject_analytic_into_reconcile_info(result, analytic)
#         return result
#
#     def _reconcile_data_by_model(self, data, reconcile_model,
#                                  reconcile_auxiliary_id):
#         new_data, new_id = super()._reconcile_data_by_model(
#             data, reconcile_model, reconcile_auxiliary_id
#         )
#         analytic = _resolve_analytic_for_statement_line(self)
#         if analytic:
#             _inject_analytic_into_data(new_data, analytic)
#         return new_data, new_id
#
#     def _get_reconcile_line(self, line, kind, is_counterpart=False,
#                             max_amount=False, from_unreconcile=False,
#                             reconcile_auxiliary_id=False, move=False,
#                             is_reconciled=False):
#         reconcile_auxiliary_id, lines = super()._get_reconcile_line(
#             line, kind,
#             is_counterpart=is_counterpart,
#             max_amount=max_amount,
#             from_unreconcile=from_unreconcile,
#             reconcile_auxiliary_id=reconcile_auxiliary_id,
#             move=move,
#             is_reconciled=is_reconciled,
#         )
#         analytic = _resolve_analytic_for_statement_line(self)
#         if analytic:
#             _inject_analytic_into_data(lines, analytic)
#         return reconcile_auxiliary_id, lines
#
#     def reconcile_bank_line(self):
#         result = super().reconcile_bank_line()
#         for st_line in self:
#             analytic = _resolve_analytic_for_statement_line(st_line)
#             if not analytic or not st_line.move_id:
#                 continue
#             # Stamp on the statement line's own move
#             _stamp_analytic_on_move(st_line.move_id, analytic)
#         return result
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def _get_user_warehouse(user):
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


def _get_warehouse_for_journal(env, journal, company_id):
    """
    Given a journal, find the ONE warehouse whose POS config uses this journal
    as a payment method.

    Returns the warehouse record or False.

    This is the core fix: we match journal → POS config → warehouse directly,
    without iterating all warehouses first (which caused cross-contamination).
    """
    if not journal:
        return False

    pos_configs = env['pos.config'].search([
        ('company_id', '=', company_id),
    ])

    for config in pos_configs:
        for pm in getattr(config, 'payment_method_ids', []):
            pm_journal = getattr(pm, 'journal_id', False)
            if pm_journal and pm_journal.id == journal.id:
                # This config owns the journal — get its warehouse
                picking_type = getattr(config, 'picking_type_id', False)
                if picking_type:
                    wh = getattr(picking_type, 'warehouse_id', False)
                    if wh:
                        _logger.debug(
                            'Journal %s → POS config %s → picking_type %s → warehouse %s',
                            journal.name, config.name, picking_type.name, wh.name,
                        )
                        return wh
                # Fallback: direct warehouse on config
                wh = getattr(config, 'warehouse_id', False)
                if wh:
                    _logger.debug(
                        'Journal %s → POS config %s → direct warehouse %s',
                        journal.name, config.name, wh.name,
                    )
                    return wh

    return False


def _resolve_analytic_for_statement_line(st_line):
    """
    Resolve the correct analytic account for a bank statement line.

    Priority:
    1. pos_session_id → config → picking_type → warehouse → analytic
       (set when Odoo links statement lines to sessions — most precise)
    2. journal → POS config (that owns this journal) → warehouse → analytic
       (for statement lines created before session linking)
    3. Current user's default warehouse (last resort for manual entries)
    """

    # --- Priority 1: Direct session link ---
    session = getattr(st_line, 'pos_session_id', False)
    if session:
        config = getattr(session, 'config_id', False)
        if config:
            picking_type = getattr(config, 'picking_type_id', False)
            if picking_type:
                wh = getattr(picking_type, 'warehouse_id', False)
                if wh and getattr(wh, 'analytic_account_id', False):
                    _logger.debug(
                        'Stmt line analytic from session %s → wh %s → %s',
                        session.name, wh.name, wh.analytic_account_id.name,
                    )
                    return wh.analytic_account_id
            wh = getattr(config, 'warehouse_id', False)
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id

    # --- Priority 2: Journal → correct POS config → warehouse ---
    journal = getattr(st_line, 'journal_id', False)
    if journal:
        wh = _get_warehouse_for_journal(
            st_line.env, journal, st_line.company_id.id
        )
        if wh and getattr(wh, 'analytic_account_id', False):
            _logger.debug(
                'Stmt line analytic from journal %s → wh %s → %s',
                journal.name, wh.name, wh.analytic_account_id.name,
            )
            return wh.analytic_account_id

    # --- Priority 3: Current user's default warehouse ---
    user = st_line.env.user
    wh = _get_user_warehouse(user)
    if wh and getattr(wh, 'analytic_account_id', False):
        _logger.debug(
            'Stmt line analytic from user warehouse: %s', wh.name
        )
        return wh.analytic_account_id

    return False


def _inject_analytic_into_data(data, analytic):
    if not data or not analytic:
        return data
    key = str(analytic.id)
    for line in data:
        existing = line.get('analytic_distribution') or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            line['analytic_distribution'] = new_dist
    return data


def _inject_analytic_into_reconcile_info(reconcile_info, analytic):
    if not reconcile_info or not analytic:
        return reconcile_info
    _inject_analytic_into_data(reconcile_info.get('data', []), analytic)
    return reconcile_info


def _stamp_analytic_on_move(move, analytic):
    """Write analytic on all lines of a move, including posted ones."""
    if not move or not analytic:
        return
    key = str(analytic.id)
    for line in move.line_ids.filtered(lambda l: l.account_id):
        existing = line.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
                _logger.debug(
                    'Stmt analytic %s → move %s line %s (%s)',
                    analytic.name, move.name, line.id, line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not set analytic on move %s line %s: %s',
                    move.name, line.id, e,
                )


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Stamp analytic on the statement line's own move at creation time.

        NOTE: pos_session_id may NOT be set yet at this point (Odoo sets it
        later). We therefore rely on Priority 2 (journal → POS config →
        warehouse) which is now correctly scoped to the exact config that
        owns the journal — no cross-warehouse contamination.
        """
        st_lines = super().create(vals_list)
        for st_line in st_lines:
            analytic = _resolve_analytic_for_statement_line(st_line)
            if analytic and st_line.move_id:
                _stamp_analytic_on_move(st_line.move_id, analytic)
        return st_lines

    def write(self, vals):
        """
        Re-stamp when pos_session_id is set after creation —
        this lets Priority 1 override any fallback applied in create().
        """
        result = super().write(vals)
        if 'pos_session_id' in vals:
            for st_line in self:
                analytic = _resolve_analytic_for_statement_line(st_line)
                if analytic and st_line.move_id:
                    _stamp_analytic_on_move(st_line.move_id, analytic)
        return result

    def _default_reconcile_data(self, from_unreconcile=False):
        result = super()._default_reconcile_data(from_unreconcile=from_unreconcile)
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    def _recompute_suspense_line(self, data, reconcile_auxiliary_id,
                                 manual_reference):
        result = super()._recompute_suspense_line(
            data, reconcile_auxiliary_id, manual_reference
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    def _reconcile_data_by_model(self, data, reconcile_model,
                                 reconcile_auxiliary_id):
        new_data, new_id = super()._reconcile_data_by_model(
            data, reconcile_model, reconcile_auxiliary_id
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_data(new_data, analytic)
        return new_data, new_id

    def _get_reconcile_line(self, line, kind, is_counterpart=False,
                            max_amount=False, from_unreconcile=False,
                            reconcile_auxiliary_id=False, move=False,
                            is_reconciled=False):
        reconcile_auxiliary_id, lines = super()._get_reconcile_line(
            line, kind,
            is_counterpart=is_counterpart,
            max_amount=max_amount,
            from_unreconcile=from_unreconcile,
            reconcile_auxiliary_id=reconcile_auxiliary_id,
            move=move,
            is_reconciled=is_reconciled,
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_data(lines, analytic)
        return reconcile_auxiliary_id, lines

    def reconcile_bank_line(self):
        result = super().reconcile_bank_line()
        for st_line in self:
            analytic = _resolve_analytic_for_statement_line(st_line)
            if not analytic or not st_line.move_id:
                continue
            _stamp_analytic_on_move(st_line.move_id, analytic)
        return result