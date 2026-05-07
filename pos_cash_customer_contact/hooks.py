import logging
_logger = logging.getLogger(__name__)

CASH_CUSTOMER_NAME = "CASH CUSTOMER"


def post_init_hook(env):
    """
    After module install/upgrade:
    1. Mark all existing CASH CUSTOMER sub-contacts with is_cash_customer_contact=True
    2. Reset their customer_rank to 0
    """
    _logger.info("PCB post_init_hook: fixing existing CASH CUSTOMER contacts...")

    env.cr.execute("""
        UPDATE res_partner child
        SET    customer_rank = 0,
               is_cash_customer_contact = TRUE
        FROM   res_partner parent
        WHERE  child.parent_id = parent.id
          AND  parent.name = %s
          AND  parent.is_company = TRUE
          AND  child.is_company = FALSE
    """, (CASH_CUSTOMER_NAME,))

    count = env.cr.rowcount
    _logger.info("PCB post_init_hook: fixed %d existing contacts.", count)