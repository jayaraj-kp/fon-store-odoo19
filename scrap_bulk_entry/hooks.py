# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Create the sequence for Scrap Bulk Entry if it does not exist yet."""
    if not env['ir.sequence'].search([('code', '=', 'scrap.bulk.entry')], limit=1):
        env['ir.sequence'].create({
            'name': 'Scrap Bulk Entry',
            'code': 'scrap.bulk.entry',
            'prefix': 'SBE/%(year)s/',
            'padding': 5,
            'company_id': False,
        })
