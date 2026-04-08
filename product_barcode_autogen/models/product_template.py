# # # # -*- coding: utf-8 -*-
# # # import random
# # # import string
# # # import logging
# # #
# # # from odoo import api, fields, models, _
# # # from odoo.exceptions import ValidationError
# # #
# # # _logger = logging.getLogger(__name__)
# # #
# # #
# # # class ProductTemplate(models.Model):
# # #     _inherit = 'product.template'
# # #
# # #     # -------------------------------------------------------------------------
# # #     # Helper: generate a unique alphanumeric barcode
# # #     # -------------------------------------------------------------------------
# # #     def _generate_barcode(self):
# # #         """Return a unique alphanumeric barcode string.
# # #
# # #         Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
# # #         Example: BC-A3F7K2M9X1Q5
# # #         """
# # #         ICP = self.env['ir.config_parameter'].sudo()
# # #         prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or 'BC').strip().upper()
# # #         try:
# # #             length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 12)
# # #             length = max(4, min(20, length))   # clamp between 4 and 20
# # #         except (ValueError, TypeError):
# # #             length = 12
# # #
# # #         chars = string.ascii_uppercase + string.digits   # A-Z + 0-9
# # #
# # #         for _attempt in range(20):          # retry up to 20 times for uniqueness
# # #             rand_part = ''.join(random.choices(chars, k=length))
# # #             candidate = f"{prefix}-{rand_part}" if prefix else rand_part
# # #
# # #             # Check uniqueness across product.template AND product.product
# # #             tmpl_exists = self.env['product.template'].sudo().search_count(
# # #                 [('barcode', '=', candidate)], limit=1
# # #             )
# # #             prod_exists = self.env['product.product'].sudo().search_count(
# # #                 [('barcode', '=', candidate)], limit=1
# # #             )
# # #             if not tmpl_exists and not prod_exists:
# # #                 return candidate
# # #
# # #         _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
# # #         return None
# # #
# # #     # -------------------------------------------------------------------------
# # #     # Override create to inject barcode
# # #     # -------------------------------------------------------------------------
# # #     @api.model_create_multi
# # #     def create(self, vals_list):
# # #         for vals in vals_list:
# # #             if not vals.get('barcode'):
# # #                 barcode = self._generate_barcode()
# # #                 if barcode:
# # #                     vals['barcode'] = barcode
# # #         return super().create(vals_list)
# # #
# # #     # -------------------------------------------------------------------------
# # #     # Button: regenerate barcode manually from the form
# # #     # -------------------------------------------------------------------------
# # #     def action_regenerate_barcode(self):
# # #         """Regenerate the barcode for this product template."""
# # #         self.ensure_one()
# # #         new_barcode = self._generate_barcode()
# # #         if new_barcode:
# # #             self.barcode = new_barcode
# # #             return {
# # #                 'type': 'ir.actions.client',
# # #                 'tag': 'display_notification',
# # #                 'params': {
# # #                     'title': _('Barcode Regenerated'),
# # #                     'message': _('New barcode: %s') % new_barcode,
# # #                     'type': 'success',
# # #                     'sticky': False,
# # #                 },
# # #             }
# # #         else:
# # #             return {
# # #                 'type': 'ir.actions.client',
# # #                 'tag': 'display_notification',
# # #                 'params': {
# # #                     'title': _('Warning'),
# # #                     'message': _('Could not generate a unique barcode. Please try again.'),
# # #                     'type': 'warning',
# # #                     'sticky': False,
# # #                 },
# # #             }
# # # -*- coding: utf-8 -*-
# # import random
# # import string
# # import logging
# #
# # from odoo import api, fields, models, _
# # from odoo.exceptions import ValidationError
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class ProductTemplate(models.Model):
# #     _inherit = 'product.template'
# #
# #     # -------------------------------------------------------------------------
# #     # Helper: generate a unique alphanumeric barcode
# #     # -------------------------------------------------------------------------
# #     def _generate_barcode(self):
# #         """Return a unique alphanumeric barcode string.
# #
# #         Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
# #         Example: BC-A3F7K2M9X1Q5
# #         """
# #         ICP = self.env['ir.config_parameter'].sudo()
# #         prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or 'BC').strip().upper()
# #         try:
# #             length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 8)
# #             length = max(4, min(20, length))   # clamp between 4 and 20
# #         except (ValueError, TypeError):
# #             length = 8
# #
# #         chars = string.ascii_uppercase + string.digits   # A-Z + 0-9
# #
# #         for _attempt in range(20):          # retry up to 20 times for uniqueness
# #             rand_part = ''.join(random.choices(chars, k=length))
# #             candidate = f"{prefix}-{rand_part}" if prefix else rand_part
# #
# #             # Check uniqueness across product.template AND product.product
# #             tmpl_exists = self.env['product.template'].sudo().search_count(
# #                 [('barcode', '=', candidate)], limit=1
# #             )
# #             prod_exists = self.env['product.product'].sudo().search_count(
# #                 [('barcode', '=', candidate)], limit=1
# #             )
# #             if not tmpl_exists and not prod_exists:
# #                 return candidate
# #
# #         _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
# #         return None
# #
# #     # -------------------------------------------------------------------------
# #     # Override create to inject barcode
# #     # -------------------------------------------------------------------------
# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         for vals in vals_list:
# #             if not vals.get('barcode'):
# #                 barcode = self._generate_barcode()
# #                 if barcode:
# #                     vals['barcode'] = barcode
# #         return super().create(vals_list)
# #
# #     # -------------------------------------------------------------------------
# #     # Button: regenerate barcode manually from the form
# #     # -------------------------------------------------------------------------
# #     def action_regenerate_barcode(self):
# #         """Regenerate the barcode for this product template."""
# #         self.ensure_one()
# #         new_barcode = self._generate_barcode()
# #         if new_barcode:
# #             self.barcode = new_barcode
# #             return {
# #                 'type': 'ir.actions.client',
# #                 'tag': 'display_notification',
# #                 'params': {
# #                     'title': _('Barcode Regenerated'),
# #                     'message': _('New barcode: %s') % new_barcode,
# #                     'type': 'success',
# #                     'sticky': False,
# #                 },
# #             }
# #         else:
# #             return {
# #                 'type': 'ir.actions.client',
# #                 'tag': 'display_notification',
# #                 'params': {
# #                     'title': _('Warning'),
# #                     'message': _('Could not generate a unique barcode. Please try again.'),
# #                     'type': 'warning',
# #                     'sticky': False,
# #                 },
# #             }
#
# # -*- coding: utf-8 -*-
# import random
# import string
# import logging
#
# from odoo import api, fields, models, _
#
# _logger = logging.getLogger(__name__)
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     # -------------------------------------------------------------------------
#     # Helper: generate a unique alphanumeric barcode
#     # -------------------------------------------------------------------------
#     def _generate_barcode(self):
#         """Return a unique alphanumeric barcode string.
#
#         Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
#         Example: BC-A3F7K2M9X1Q5
#         """
#         ICP = self.env['ir.config_parameter'].sudo()
#         prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or 'BC').strip().upper()
#         try:
#             length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 8)
#             length = max(4, min(20, length))
#         except (ValueError, TypeError):
#             length = 8
#
#         chars = string.ascii_uppercase + string.digits  # A-Z + 0-9
#
#         for _attempt in range(20):
#             rand_part = ''.join(random.choices(chars, k=length))
#             candidate = f"{prefix}-{rand_part}" if prefix else rand_part
#
#             tmpl_exists = self.env['product.template'].sudo().search_count(
#                 [('barcode', '=', candidate)], limit=1
#             )
#             prod_exists = self.env['product.product'].sudo().search_count(
#                 [('barcode', '=', candidate)], limit=1
#             )
#             if not tmpl_exists and not prod_exists:
#                 return candidate
#
#         _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
#         return None
#
#     # -------------------------------------------------------------------------
#     # Override create: auto-generate ONLY when barcode is not manually provided
#     # -------------------------------------------------------------------------
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if not vals.get('barcode'):
#                 # No barcode entered by user — auto-generate one
#                 barcode = self._generate_barcode()
#                 if barcode:
#                     vals['barcode'] = barcode
#             # If barcode IS provided by user, leave it completely untouched
#         return super().create(vals_list)
#
#     # -------------------------------------------------------------------------
#     # Override write: NEVER auto-generate if user is manually setting a barcode
#     # and NEVER wipe a manually entered barcode with auto-generated one
#     # -------------------------------------------------------------------------
#     def write(self, vals):
#         # If the write call is explicitly setting barcode (even to empty string),
#         # let it through as-is — user intention takes priority
#         if 'barcode' in vals:
#             return super().write(vals)
#
#         # For records that currently have NO barcode (e.g. imported products),
#         # do NOT auto-generate on write — only generate on create
#         return super().write(vals)
#
#     # -------------------------------------------------------------------------
#     # Button: regenerate barcode manually from the form
#     # -------------------------------------------------------------------------
#     def action_regenerate_barcode(self):
#         """Regenerate the barcode for this product template."""
#         self.ensure_one()
#         new_barcode = self._generate_barcode()
#         if new_barcode:
#             self.barcode = new_barcode
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Barcode Regenerated'),
#                     'message': _('New barcode: %s') % new_barcode,
#                     'type': 'success',
#                     'sticky': False,
#                 },
#             }
#         else:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Warning'),
#                     'message': _('Could not generate a unique barcode. Please try again.'),
#                     'type': 'warning',
#                     'sticky': False,
#                 },
#             }

# # # -*- coding: utf-8 -*-
# # import random
# # import string
# # import logging
# #
# # from odoo import api, fields, models, _
# # from odoo.exceptions import ValidationError
# #
# # _logger = logging.getLogger(__name__)
# #
# #
# # class ProductTemplate(models.Model):
# #     _inherit = 'product.template'
# #
# #     # -------------------------------------------------------------------------
# #     # Helper: generate a unique alphanumeric barcode
# #     # -------------------------------------------------------------------------
# #     def _generate_barcode(self):
# #         """Return a unique alphanumeric barcode string.
# #
# #         Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
# #         Example: BC-A3F7K2M9X1Q5
# #         """
# #         ICP = self.env['ir.config_parameter'].sudo()
# #         prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or 'BC').strip().upper()
# #         try:
# #             length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 12)
# #             length = max(4, min(20, length))   # clamp between 4 and 20
# #         except (ValueError, TypeError):
# #             length = 12
# #
# #         chars = string.ascii_uppercase + string.digits   # A-Z + 0-9
# #
# #         for _attempt in range(20):          # retry up to 20 times for uniqueness
# #             rand_part = ''.join(random.choices(chars, k=length))
# #             candidate = f"{prefix}-{rand_part}" if prefix else rand_part
# #
# #             # Check uniqueness across product.template AND product.product
# #             tmpl_exists = self.env['product.template'].sudo().search_count(
# #                 [('barcode', '=', candidate)], limit=1
# #             )
# #             prod_exists = self.env['product.product'].sudo().search_count(
# #                 [('barcode', '=', candidate)], limit=1
# #             )
# #             if not tmpl_exists and not prod_exists:
# #                 return candidate
# #
# #         _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
# #         return None
# #
# #     # -------------------------------------------------------------------------
# #     # Override create to inject barcode
# #     # -------------------------------------------------------------------------
# #     @api.model_create_multi
# #     def create(self, vals_list):
# #         for vals in vals_list:
# #             if not vals.get('barcode'):
# #                 barcode = self._generate_barcode()
# #                 if barcode:
# #                     vals['barcode'] = barcode
# #         return super().create(vals_list)
# #
# #     # -------------------------------------------------------------------------
# #     # Button: regenerate barcode manually from the form
# #     # -------------------------------------------------------------------------
# #     def action_regenerate_barcode(self):
# #         """Regenerate the barcode for this product template."""
# #         self.ensure_one()
# #         new_barcode = self._generate_barcode()
# #         if new_barcode:
# #             self.barcode = new_barcode
# #             return {
# #                 'type': 'ir.actions.client',
# #                 'tag': 'display_notification',
# #                 'params': {
# #                     'title': _('Barcode Regenerated'),
# #                     'message': _('New barcode: %s') % new_barcode,
# #                     'type': 'success',
# #                     'sticky': False,
# #                 },
# #             }
# #         else:
# #             return {
# #                 'type': 'ir.actions.client',
# #                 'tag': 'display_notification',
# #                 'params': {
# #                     'title': _('Warning'),
# #                     'message': _('Could not generate a unique barcode. Please try again.'),
# #                     'type': 'warning',
# #                     'sticky': False,
# #                 },
# #             }
# # -*- coding: utf-8 -*-
# import random
# import string
# import logging
#
# from odoo import api, fields, models, _
# from odoo.exceptions import ValidationError
#
# _logger = logging.getLogger(__name__)
#
#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     # -------------------------------------------------------------------------
#     # Helper: generate a unique alphanumeric barcode
#     # -------------------------------------------------------------------------
#     def _generate_barcode(self):
#         """Return a unique alphanumeric barcode string.
#
#         Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
#         Example: BC-A3F7K2M9X1Q5
#         """
#         ICP = self.env['ir.config_parameter'].sudo()
#         prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or 'BC').strip().upper()
#         try:
#             length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 8)
#             length = max(4, min(20, length))   # clamp between 4 and 20
#         except (ValueError, TypeError):
#             length = 8
#
#         chars = string.ascii_uppercase + string.digits   # A-Z + 0-9
#
#         for _attempt in range(20):          # retry up to 20 times for uniqueness
#             rand_part = ''.join(random.choices(chars, k=length))
#             candidate = f"{prefix}-{rand_part}" if prefix else rand_part
#
#             # Check uniqueness across product.template AND product.product
#             tmpl_exists = self.env['product.template'].sudo().search_count(
#                 [('barcode', '=', candidate)], limit=1
#             )
#             prod_exists = self.env['product.product'].sudo().search_count(
#                 [('barcode', '=', candidate)], limit=1
#             )
#             if not tmpl_exists and not prod_exists:
#                 return candidate
#
#         _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
#         return None
#
#     # -------------------------------------------------------------------------
#     # Override create to inject barcode
#     # -------------------------------------------------------------------------
#     @api.model_create_multi
#     def create(self, vals_list):
#         for vals in vals_list:
#             if not vals.get('barcode'):
#                 barcode = self._generate_barcode()
#                 if barcode:
#                     vals['barcode'] = barcode
#         return super().create(vals_list)
#
#     # -------------------------------------------------------------------------
#     # Button: regenerate barcode manually from the form
#     # -------------------------------------------------------------------------
#     def action_regenerate_barcode(self):
#         """Regenerate the barcode for this product template."""
#         self.ensure_one()
#         new_barcode = self._generate_barcode()
#         if new_barcode:
#             self.barcode = new_barcode
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Barcode Regenerated'),
#                     'message': _('New barcode: %s') % new_barcode,
#                     'type': 'success',
#                     'sticky': False,
#                 },
#             }
#         else:
#             return {
#                 'type': 'ir.actions.client',
#                 'tag': 'display_notification',
#                 'params': {
#                     'title': _('Warning'),
#                     'message': _('Could not generate a unique barcode. Please try again.'),
#                     'type': 'warning',
#                     'sticky': False,
#                 },
#             }

# -*- coding: utf-8 -*-
import random
import string
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # Helper: generate a unique alphanumeric barcode
    # -------------------------------------------------------------------------
    def _generate_barcode(self):
        """Return a unique alphanumeric barcode string.

        Format: <PREFIX>-<RANDOM_ALPHANUMERIC>
        Example: BC-A3F7K2M9X1Q5
        """
        ICP = self.env['ir.config_parameter'].sudo()
        prefix = (ICP.get_param('product_barcode_autogen.barcode_prefix') or '').strip().upper()
        try:
            length = int(ICP.get_param('product_barcode_autogen.barcode_length') or 8)
            length = max(4, min(20, length))
        except (ValueError, TypeError):
            length = 10

        chars = string.ascii_uppercase + string.digits  # A-Z + 0-9

        for _attempt in range(20):
            rand_part = ''.join(random.choices(chars, k=length))
            candidate = f"{prefix}-{rand_part}" if prefix else rand_part

            tmpl_exists = self.env['product.template'].sudo().search_count(
                [('barcode', '=', candidate)], limit=1
            )
            prod_exists = self.env['product.product'].sudo().search_count(
                [('barcode', '=', candidate)], limit=1
            )
            if not tmpl_exists and not prod_exists:
                return candidate

        _logger.warning("product_barcode_autogen: could not find unique barcode after 20 attempts.")
        return None

    # -------------------------------------------------------------------------
    # Override create: auto-generate ONLY when barcode is not manually provided
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                # No barcode entered by user — auto-generate one
                barcode = self._generate_barcode()
                if barcode:
                    vals['barcode'] = barcode
            # If barcode IS provided by user, leave it completely untouched
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Override write: NEVER auto-generate if user is manually setting a barcode
    # and NEVER wipe a manually entered barcode with auto-generated one
    # -------------------------------------------------------------------------
    def write(self, vals):
        # If the write call is explicitly setting barcode (even to empty string),
        # let it through as-is — user intention takes priority
        if 'barcode' in vals:
            return super().write(vals)

        # For records that currently have NO barcode (e.g. imported products),
        # do NOT auto-generate on write — only generate on create
        return super().write(vals)

    # -------------------------------------------------------------------------
    # Button: regenerate barcode manually from the form
    # -------------------------------------------------------------------------
    def action_regenerate_barcode(self):
        """Regenerate the barcode for this product template."""
        self.ensure_one()
        new_barcode = self._generate_barcode()
        if new_barcode:
            self.barcode = new_barcode
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Barcode Regenerated'),
                    'message': _('New barcode: %s') % new_barcode,
                    'type': 'success',
                    'sticky': False,
                },
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('Could not generate a unique barcode. Please try again.'),
                    'type': 'warning',
                    'sticky': False,
                },
            }