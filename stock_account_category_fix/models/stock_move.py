from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    # AVCO Interim Account Fix
    # -------------------------------------------------------------------------
    # Problem (Odoo 19 CE):
    #   When a purchase receipt is validated for an AVCO product, Odoo CE
    #   credits the Stock Interim (Received) account at the NEW AVCO price
    #   instead of the actual PO line price.
    #
    #   Example from the image:
    #     Opening stock : 10 units @ 50  = 500
    #     Purchased     : 10 units @ 55  = 550
    #     New AVCO      : 1050 / 20      = 52.50
    #
    #   CE (wrong): Receipt journal entry → Dr Stock 525 / Cr Interim 525 (at 52.50)
    #   Vendor bill              → Dr Interim 550 / Cr AP 550 (at 55.00)
    #   → 25.00 remains uncleared in the interim account forever.
    #
    #   Correct: Receipt entry → Dr Stock 525 / Cr Interim 550 (at PO price)
    #            with the 25 difference auto-posted to a price-difference account.
    #
    # Fix:
    #   Override _get_price_unit() so that for purchase receipts with AVCO
    #   the PO price is returned. This makes the SVL record at PO price (correct
    #   actual cost), the AVCO recalculation still works because Odoo recalculates
    #   AVCO from cumulative SVL values, and the interim account is credited at
    #   the real invoice price.
    # -------------------------------------------------------------------------

    def _get_price_unit(self):
        """
        For purchase receipts of AVCO-costed products, return the PO unit price
        (converted to company currency) instead of the current moving average.

        This ensures:
          1. Stock Interim (Received) is credited at the true purchase cost.
          2. Vendor bill reconciles cleanly with zero residual in the interim account.
          3. AVCO is recalculated correctly from actual SVL values.
        """
        price_unit = super()._get_price_unit()

        # Only apply to incoming purchase moves (receipts)
        if not self.purchase_line_id:
            return price_unit

        if self.location_dest_id.usage != 'internal':
            return price_unit

        categ = self.product_id.categ_id
        if categ.property_valuation != 'real_time':
            return price_unit
        if self.product_id.cost_method != 'average':
            return price_unit

        # ---- Fetch PO price in company currency ----
        po_line = self.purchase_line_id
        po_price = po_line.price_unit

        # Strip included taxes to get the untaxed unit price
        if po_line.taxes_id:
            tax_res = po_line.taxes_id.with_context(round=False).compute_all(
                po_price,
                currency=po_line.currency_id,
                quantity=1.0,
                product=self.product_id,
                partner=self.picking_id.partner_id if self.picking_id else False,
            )
            po_price = tax_res['total_excluded']

        # Convert from PO currency to company currency
        if po_line.currency_id and po_line.currency_id != self.company_id.currency_id:
            po_price = po_line.currency_id._convert(
                po_price,
                self.company_id.currency_id,
                self.company_id,
                self.date or fields.Date.today(),
            )

        # Adjust for UoM difference between move and product's internal UoM
        if self.product_uom and self.product_uom != self.product_id.uom_id:
            po_price = self.product_uom._compute_price(po_price, self.product_id.uom_id)

        if po_price and po_price != price_unit:
            _logger.debug(
                "AVCO receipt fix — product '%s': replacing AVCO price %.4f "
                "with PO price %.4f for interim account.",
                self.product_id.display_name, price_unit, po_price,
            )

        return po_price or price_unit
