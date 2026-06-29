# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import traceback

from odoo.tools.safe_eval import safe_eval

from .data_error import DataError, NameDataError

__all__ = ["mis_safe_eval"]


def mis_safe_eval(expr, locals_dict):
    """Evaluate an expression using safe_eval

    Returns the evaluated value or DataError.

    Raises NameError if the evaluation depends on a variable that is not
    present in local_dict.
    """
    try:
        val = safe_eval(expr, locals_dict or {})
    except NameError:
        val = NameDataError("#NAME", traceback.format_exc())
    except ZeroDivisionError:
        # pylint: disable=redefined-variable-type
        val = DataError("#DIV/0", traceback.format_exc())
    except ValueError as e:
        orig_exc = e.__cause__ or e.__context__
        if isinstance(orig_exc, NameError) or "NameError" in str(e):
            val = NameDataError("#NAME", traceback.format_exc())
        elif isinstance(orig_exc, ZeroDivisionError) or "ZeroDivisionError" in str(e):
            val = DataError("#DIV/0", traceback.format_exc())
        else:
            val = DataError("#ERR", traceback.format_exc())
    except Exception:
        val = DataError("#ERR", traceback.format_exc())
    return val

