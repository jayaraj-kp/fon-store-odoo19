# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """
    Automatically migrate any existing cross-WH internal transfers
    to go through the Inter-warehouse transit location.
    Runs once on module install, and on every upgrade.
    """
    env['stock.picking']._migrate_cross_wh_transfers()