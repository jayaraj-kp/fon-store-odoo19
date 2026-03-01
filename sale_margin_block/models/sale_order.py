# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ── Order-level margin summary ────────────────────────────────────────────
    smb_order_margin_percent = fields.Float(
        string='Order Margin %',
        compute='_compute_smb_order_margin',
        store=True,
        digits=(5, 2),
    )
    smb_order_margin_amount = fields.Monetary(
        string='Order Margin',
        compute='_compute_smb_order_margin',
        store=True,
    )
    smb_has_threshold_breach = fields.Boolean(
        string='Has Threshold Breach',
        compute='_compute_smb_order_margin',
        store=True,
        help='True when at least one line breaches margin/cost thresholds.',
    )

    @api.depends(
        'order_line.smb_margin_amount',
        'order_line.smb_margin_percent',
        'order_line.smb_below_threshold',
        'amount_untaxed',
    )
    def _compute_smb_order_margin(self):
        for order in self:
            total_cost = sum(
                l.smb_unit_cost * l.product_uom_qty for l in order.order_line
            )
            total_subtotal = order.amount_untaxed

            order.smb_order_margin_amount = total_subtotal - total_cost

            if total_subtotal:
                order.smb_order_margin_percent = (
                    (total_subtotal - total_cost) / total_subtotal
                ) * 100.0
            else:
                order.smb_order_margin_percent = 0.0

            order.smb_has_threshold_breach = any(
                l.smb_below_threshold for l in order.order_line if l.product_id
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _smb_get_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        return {
            'margin_enabled': ICP.get_param('sale_margin_block.margin_block_enabled', 'False') == 'True',
            'margin_min': float(ICP.get_param('sale_margin_block.margin_minimum', '0')),
            'cost_enabled': ICP.get_param('sale_margin_block.cost_block_enabled', 'False') == 'True',
            'cost_min': float(ICP.get_param('sale_margin_block.cost_minimum', '100')),
            'warn_only': ICP.get_param('sale_margin_block.warn_only', 'False') == 'True',
        }

    def _smb_is_manager(self):
        return self.env.user.has_group('sale_margin_block.group_sale_margin_manager')

    def _smb_collect_violations(self, params):
        """Return a list of human-readable violation strings."""
        violations = []
        for line in self.order_line:
            if not line.product_id:
                continue
            msgs = []
            if params['margin_enabled'] and line.smb_margin_percent < params['margin_min']:
                msgs.append(
                    _('Margin %(actual).2f%% < minimum %(min).2f%%',
                      actual=line.smb_margin_percent,
                      min=params['margin_min'])
                )
            if params['cost_enabled'] and line.smb_cost_recovery_percent < params['cost_min']:
                msgs.append(
                    _('Cost recovery %(actual).2f%% < minimum %(min).2f%%',
                      actual=line.smb_cost_recovery_percent,
                      min=params['cost_min'])
                )
            if msgs:
                violations.append(
                    _('• [%(ref)s] %(name)s: %(issues)s',
                      ref=line.product_id.default_code or line.product_id.id,
                      name=line.product_id.name,
                      issues='; '.join(msgs))
                )
        return violations

    def _smb_validate(self, action_label='confirm'):
        """Core validation; raises UserError if blocked."""
        params = self._smb_get_params()
        if not params['margin_enabled'] and not params['cost_enabled']:
            return  # nothing configured

        for order in self:
            violations = order._smb_collect_violations(params)
            if not violations:
                continue

            header = _(
                'Order %(name)s cannot be %(action)s because the following lines '
                'breach the configured thresholds:\n\n',
                name=order.name,
                action=action_label,
            )
            body = '\n'.join(violations)

            if params['warn_only'] or self._smb_is_manager():
                # soft warning — log a chatter note but do NOT block
                order.message_post(
                    body=header + body,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            else:
                raise UserError(header + body)

    # ── Override action_confirm ───────────────────────────────────────────────

    def action_confirm(self):
        self._smb_validate(action_label=_('confirmed'))
        return super().action_confirm()

    # ── Override _create_invoices (called by "Create Invoice" wizard) ─────────

    def _create_invoices(self, grouped=False, final=False, date=None):
        self._smb_validate(action_label=_('invoiced'))
        return super()._create_invoices(grouped=grouped, final=final, date=date)
