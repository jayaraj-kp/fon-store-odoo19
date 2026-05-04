# from odoo import fields, models
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class StockMove(models.Model):
#     _inherit = 'stock.move'
#
#     # -------------------------------------------------------------------------
#     # AVCO Interim Account Fix
#     # -------------------------------------------------------------------------
#     # Problem (Odoo 19 CE):
#     #   When a purchase receipt is validated for an AVCO product, Odoo CE
#     #   credits the Stock Interim (Received) account at the NEW AVCO price
#     #   instead of the actual PO line price.
#     #
#     #   Example from the image:
#     #     Opening stock : 10 units @ 50  = 500
#     #     Purchased     : 10 units @ 55  = 550
#     #     New AVCO      : 1050 / 20      = 52.50
#     #
#     #   CE (wrong): Receipt journal entry → Dr Stock 525 / Cr Interim 525 (at 52.50)
#     #   Vendor bill              → Dr Interim 550 / Cr AP 550 (at 55.00)
#     #   → 25.00 remains uncleared in the interim account forever.
#     #
#     #   Correct: Receipt entry → Dr Stock 525 / Cr Interim 550 (at PO price)
#     #            with the 25 difference auto-posted to a price-difference account.
#     #
#     # Fix:
#     #   Override _get_price_unit() so that for purchase receipts with AVCO
#     #   the PO price is returned. This makes the SVL record at PO price (correct
#     #   actual cost), the AVCO recalculation still works because Odoo recalculates
#     #   AVCO from cumulative SVL values, and the interim account is credited at
#     #   the real invoice price.
#     # -------------------------------------------------------------------------
#
#     def _get_price_unit(self):
#         """
#         For purchase receipts of AVCO-costed products, return the PO unit price
#         (converted to company currency) instead of the current moving average.
#
#         This ensures:
#           1. Stock Interim (Received) is credited at the true purchase cost.
#           2. Vendor bill reconciles cleanly with zero residual in the interim account.
#           3. AVCO is recalculated correctly from actual SVL values.
#         """
#         price_unit = super()._get_price_unit()
#
#         # Only apply to incoming purchase moves (receipts)
#         if not self.purchase_line_id:
#             return price_unit
#
#         if self.location_dest_id.usage != 'internal':
#             return price_unit
#
#         categ = self.product_id.categ_id
#         if categ.property_valuation != 'real_time':
#             return price_unit
#         if self.product_id.cost_method != 'average':
#             return price_unit
#
#         # ---- Fetch PO price in company currency ----
#         po_line = self.purchase_line_id
#         po_price = po_line.price_unit
#
#         # Strip included taxes to get the untaxed unit price
#         if po_line.taxes_id:
#             tax_res = po_line.taxes_id.with_context(round=False).compute_all(
#                 po_price,
#                 currency=po_line.currency_id,
#                 quantity=1.0,
#                 product=self.product_id,
#                 partner=self.picking_id.partner_id if self.picking_id else False,
#             )
#             po_price = tax_res['total_excluded']
#
#         # Convert from PO currency to company currency
#         if po_line.currency_id and po_line.currency_id != self.company_id.currency_id:
#             po_price = po_line.currency_id._convert(
#                 po_price,
#                 self.company_id.currency_id,
#                 self.company_id,
#                 self.date or fields.Date.today(),
#             )
#
#         # Adjust for UoM difference between move and product's internal UoM
#         if self.product_uom and self.product_uom != self.product_id.uom_id:
#             po_price = self.product_uom._compute_price(po_price, self.product_id.uom_id)
#
#         if po_price and po_price != price_unit:
#             _logger.debug(
#                 "AVCO receipt fix — product '%s': replacing AVCO price %.4f "
#                 "with PO price %.4f for interim account.",
#                 self.product_id.display_name, price_unit, po_price,
#             )
#
#         return po_price or price_unit
from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    # -------------------------------------------------------------------------
    # AVCO Interim Account Fix  (Odoo 19 CE)
    # -------------------------------------------------------------------------
    #
    # PROBLEM:
    #   On a purchase receipt for an AVCO product, Odoo 19 CE generates:
    #
    #       DR  110100  Stock Valuation          525   ← correct (new AVCO × qty)
    #       CR  230300  Stock Interim (Received) 525   ← WRONG  (should be PO price × qty)
    #
    #   When the vendor bill is posted it debits Interim at PO price:
    #       DR  230300  Stock Interim            550
    #       CR  AP                               550
    #
    #   This leaves a permanent ₹25 residual in the interim account.
    #
    # CORRECT BEHAVIOUR:
    #       DR  110100  Stock Valuation          525   (AVCO value — inventory cost)
    #       CR  230300  Stock Interim (Received) 550   (PO price  — matches vendor bill)
    #       DR  611000  Price Difference          25   (balancing — P&L)
    #
    # HOW ODOO BUILDS THE JOURNAL ENTRY:
    #   _action_done()
    #     └─ _create_in_svl()           → writes stock.valuation.layer at AVCO
    #     └─ _account_entry_move()
    #          └─ _generate_valuation_lines_data()   ← builds debit/credit dicts
    #          └─ _create_account_move_line()        ← posts to account.move
    #
    #   _generate_valuation_lines_data() uses `self.value` (the SVL value = AVCO × qty)
    #   for BOTH the stock debit AND the interim credit — that is the bug.
    #
    # FIX STRATEGY:
    #   1. _get_price_unit()                → returns PO price so SVL is written at
    #                                         PO price (makes stock value = PO price).
    #                                         (kept for non-AVCO paths and UoM/currency)
    #
    #   2. _generate_valuation_lines_data() → for AVCO purchase receipts:
    #        • stock debit   = SVL value (AVCO × qty)  — unchanged
    #        • interim credit = PO price × qty         — FIXED
    #        • price diff debit/credit = difference    — new balancing line
    #
    # NOTE on SVL value with this fix:
    #   Because _get_price_unit() now returns the PO price, _create_in_svl()
    #   writes the SVL at PO price (₹550), and Odoo recalculates AVCO from
    #   cumulative SVL values:  (500 + 550) / 20 = 52.50  — still correct.
    #   The stock debit in the journal entry = SVL value = ₹550 (PO price),
    #   interim credit = ₹550, price diff = ₹0 in this path.
    #
    #   If for any reason _get_price_unit() is NOT overridden (e.g. super() is
    #   called from a third module), _generate_valuation_lines_data() still
    #   fixes the interim line independently.
    # -------------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Helper: get PO unit price in company currency (tax-excluded, UoM adjusted)
    # ------------------------------------------------------------------

    def _get_po_price_in_company_currency(self):
        """
        Returns the untaxed PO unit price in company currency, adjusted for
        UoM if the move UoM differs from the product's internal UoM.

        Returns None if this is not a purchase receipt or not AVCO.
        """
        if not self.purchase_line_id:
            return None
        if self.location_dest_id.usage != 'internal':
            return None

        categ = self.product_id.categ_id
        if categ.property_valuation != 'real_time':
            return None
        if self.product_id.cost_method != 'average':
            return None

        po_line = self.purchase_line_id
        po_price = po_line.price_unit

        # Strip tax-included taxes
        if po_line.taxes_id:
            tax_res = po_line.taxes_id.with_context(round=False).compute_all(
                po_price,
                currency=po_line.currency_id,
                quantity=1.0,
                product=self.product_id,
                partner=self.picking_id.partner_id if self.picking_id else False,
            )
            po_price = tax_res['total_excluded']

        # Convert to company currency
        if po_line.currency_id and po_line.currency_id != self.company_id.currency_id:
            po_price = po_line.currency_id._convert(
                po_price,
                self.company_id.currency_id,
                self.company_id,
                self.date or fields.Date.today(),
            )

        # Adjust for UoM
        if self.product_uom and self.product_uom != self.product_id.uom_id:
            po_price = self.product_uom._compute_price(po_price, self.product_id.uom_id)

        return po_price or None

    # ------------------------------------------------------------------
    # Fix 1: _get_price_unit — return PO price so SVL is at actual cost
    # ------------------------------------------------------------------

    def _get_price_unit(self):
        """
        For AVCO purchase receipts, return the PO unit price instead of the
        current moving average so that the Stock Valuation Layer (SVL) is
        written at the actual purchase cost.
        """
        po_price = self._get_po_price_in_company_currency()
        if po_price is not None:
            avco_price = super()._get_price_unit()
            if po_price != avco_price:
                _logger.debug(
                    "AVCO _get_price_unit fix — '%s': AVCO=%.4f → PO=%.4f",
                    self.product_id.display_name, avco_price, po_price,
                )
            return po_price
        return super()._get_price_unit()

    # ------------------------------------------------------------------
    # Fix 2: _generate_valuation_lines_data — split interim vs stock value
    # ------------------------------------------------------------------

    def _generate_valuation_lines_data(
        self, partner_id, qty, debit_value, credit_value, debit_account_id,
        credit_account_id, svl_id, description
    ):
        """
        For AVCO purchase receipts:

          Standard Odoo posts:
              DR  Stock Valuation    value   (= AVCO × qty)
              CR  Stock Interim      value   (= AVCO × qty)  ← WRONG

          This override posts:
              DR  Stock Valuation    avco_value              (= AVCO × qty)
              CR  Stock Interim      po_value                (= PO price × qty)
              DR  Price Difference   diff     (if po > avco) (= po_value - avco_value)
           OR
              CR  Price Difference   diff     (if avco > po) (= avco_value - po_value)

        The result: Stock Interim is always credited at the exact PO amount,
        so the vendor bill (which debits Interim at the same PO amount) clears
        it to zero with no residual.
        """
        rslt = super()._generate_valuation_lines_data(
            partner_id, qty, debit_value, credit_value,
            debit_account_id, credit_account_id, svl_id, description
        )

        # Only apply to purchase receipts (incoming moves with a PO line)
        if not self.purchase_line_id:
            return rslt
        if self.location_dest_id.usage != 'internal':
            return rslt

        categ = self.product_id.categ_id
        if categ.property_valuation != 'real_time':
            return rslt
        if self.product_id.cost_method != 'average':
            return rslt

        # Get the actual PO price × qty (what the vendor will bill)
        po_price = self._get_po_price_in_company_currency()
        if not po_price:
            return rslt

        # Qty to use: move qty_done in product UoM converted to internal UoM
        move_qty = self.product_uom_qty
        if self.quantity_done:
            move_qty = self.quantity_done

        po_total = self.company_id.currency_id.round(po_price * move_qty)
        stock_total = credit_value  # what Odoo calculated (AVCO × qty)

        diff = self.company_id.currency_id.round(po_total - stock_total)

        if self.company_id.currency_id.is_zero(diff):
            # PO price == AVCO price, no change needed
            return rslt

        _logger.info(
            "AVCO interim fix — '%s': stock_value=%.2f  po_value=%.2f  diff=%.2f",
            self.product_id.display_name, stock_total, po_total, diff,
        )

        # Find the price difference account from the product category
        price_diff_account = self._get_price_diff_account()
        if not price_diff_account:
            _logger.warning(
                "AVCO interim fix — '%s': no price difference account found; "
                "interim account will NOT be corrected.",
                self.product_id.display_name,
            )
            return rslt

        # ---- Update the interim (credit) line to use PO price ----
        # rslt is a dict: keys are typically 'debit_line_vals' and 'credit_line_vals'
        if 'credit_line_vals' in rslt:
            rslt['credit_line_vals']['credit'] = po_total
            rslt['credit_line_vals']['debit'] = 0.0
            _logger.debug(
                "AVCO interim fix: credit line updated to %.2f (was %.2f)",
                po_total, stock_total,
            )

        # ---- Add a price difference line to balance the entry ----
        # If PO > AVCO: extra debit on price diff account
        # If AVCO > PO: extra credit on price diff account (negative diff)
        if diff > 0:
            # PO price > AVCO: debit price difference account
            price_diff_line = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': move_qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'debit': diff,
                'credit': 0.0,
                'account_id': price_diff_account.id,
            }
        else:
            # AVCO > PO: credit price difference account
            price_diff_line = {
                'name': description,
                'product_id': self.product_id.id,
                'quantity': move_qty,
                'product_uom_id': self.product_id.uom_id.id,
                'ref': description,
                'partner_id': partner_id,
                'debit': 0.0,
                'credit': abs(diff),
                'account_id': price_diff_account.id,
            }

        rslt['price_diff_line_vals'] = price_diff_line

        return rslt

    # ------------------------------------------------------------------
    # Helper: resolve price difference account
    # ------------------------------------------------------------------

    def _get_price_diff_account(self):
        """
        Returns the price difference account for AVCO purchase receipt corrections.

        Resolution order:
          1. product.product → property_account_creditor_price_difference
          2. product.template → property_account_creditor_price_difference
          3. product.category → property_account_creditor_price_difference_categ
          4. Fallback: search for account by code '611000' or name 'Price Difference'
        """
        product = self.product_id

        # 1. Product-level
        acct = getattr(product, 'property_account_creditor_price_difference', False)
        if acct:
            return acct

        # 2. Template-level
        acct = getattr(product.product_tmpl_id, 'property_account_creditor_price_difference', False)
        if acct:
            return acct

        # 3. Category-level
        acct = getattr(product.categ_id, 'property_account_creditor_price_difference_categ', False)
        if acct:
            return acct

        # 4. Fallback: search by code then name
        Account = self.env['account.account']
        acct = (
            Account.search([
                ('code', '=', '611000'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            or Account.search([
                ('name', 'ilike', 'Price Difference'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            or Account.search([
                ('name', 'ilike', 'Stock Variation'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        )

        if acct:
            _logger.debug(
                "AVCO price diff account resolved via fallback search: %s %s",
                acct.code, acct.name,
            )
        return acct or False