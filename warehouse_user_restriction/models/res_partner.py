from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-apply default customer tags from the creating user."""
        user = self.env.user
        default_tags = user.default_customer_tag_ids

        if default_tags:
            for vals in vals_list:
                # Only apply to customers (is_customer flag) or if no type specified
                # Apply tags to any new contact created by this user
                existing_tags = vals.get('category_id', [])
                # Merge existing tags with default tags
                tag_ids = list(set(
                    [tag.id for tag in default_tags] +
                    [cmd[1] for cmd in existing_tags if isinstance(cmd, (list, tuple)) and len(cmd) > 1 and cmd[0] == 4] +
                    [cmd[1] for cmd in existing_tags if isinstance(cmd, (list, tuple)) and len(cmd) > 1 and cmd[0] == 1]
                ))
                # Build proper Many2many command
                if tag_ids:
                    vals['category_id'] = [(6, 0, tag_ids)]

        return super().create(vals_list)
