# -*- coding: utf-8 -*-
from . import models
from . import hooks
def post_init_hook(env):
    """
    No-op hook — required because a previous installation of this module
    registered a post_init_hook in the ir.module.module database record.
    Odoo will call this on (re)install; it is intentionally empty.
    """
    pass
