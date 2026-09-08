# ─────────────────────────────────────────────────────────────────────────────
# Shared request-level cache helper.
#
# Used by pos_config.py and stock_picking.py to avoid re-running the same
# SQL/search queries multiple times within a single HTTP request.
#
# The cache lives on the DB cursor (cr), which Odoo creates fresh for every
# request and discards afterward — so this is 100% request-scoped and never
# leaks stale data between requests or users.
# ─────────────────────────────────────────────────────────────────────────────

def get_request_cache(cr):
    """Return a per-request dict attached to the DB cursor."""
    if not hasattr(cr, '_whr_cache'):
        cr._whr_cache = {}
    return cr._whr_cache


def cache_key(prefix, user_id):
    return '%s_%s' % (prefix, user_id)