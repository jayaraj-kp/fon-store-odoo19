# -*- coding: utf-8 -*-
from . import models
# Import function directly so Odoo can find it as a root-level attribute:
# odoo.addons.internal_journal_entry.post_init_hook
from .hooks import post_init_hook
