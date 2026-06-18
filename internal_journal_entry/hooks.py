# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    After module install:
    - Assign the default 'Stock Transfer Journal' and 'Stock Transfer Account'
      to every existing company so the module works out-of-the-box.
    """
    _logger.info('internal_journal_entry: running post_init_hook …')

    journal = env.ref(
        'internal_journal_entry.stock_internal_transfer_journal',
        raise_if_not_found=False,
    )
    account = env.ref(
        'internal_journal_entry.stock_internal_transfer_account',
        raise_if_not_found=False,
    )

    companies = env['res.company'].sudo().search([])
    for company in companies:
        if journal and not company.internal_transfer_journal_id:
            company.internal_transfer_journal_id = journal.id
            _logger.info(
                'Set default Stock Transfer Journal for company: %s', company.name
            )
        if account and not company.internal_transfer_account_id:
            company.internal_transfer_account_id = account.id
            _logger.info(
                'Set default Stock Transfer Account for company: %s', company.name
            )

    _logger.info('internal_journal_entry: post_init_hook complete.')
