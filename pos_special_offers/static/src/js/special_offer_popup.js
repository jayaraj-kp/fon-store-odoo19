/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SpecialOfferPopup extends Component {
    static template = "pos_special_offers.SpecialOfferPopup";
    static props = {
        products:   Array,
        categories: Array,
        close:      Function,
    };

    setup() {
        this.orm = useService("orm");
        this.offerService = useService("special_offer_service");
        this.state = useState({
            offerName:     "",
            offerType:     "flat_discount",
            couponCode:    "",
            selProducts:   [],
            selCategory:   "",
            dateFrom:      this._today(),
            dateTo:        this._today(),
            activeTime:    "00:00",
            discountType:  "percentage",
            discountValue: "10",
            purchaseLimit: "0",
            loading:       false,
            successMsg:    "",
            errorMsg:      "",
        });
    }

    _today() { return new Date().toISOString().split("T")[0]; }

    // Explicit handlers for every field — avoids arrow function `this` context loss in OWL templates
    onOfferName(ev)     { this.state.offerName     = ev.target.value; }
    onOfferType(ev)     { this.state.offerType     = ev.target.value; }
    onCouponCode(ev)    { this.state.couponCode    = ev.target.value; }
    onSelCategory(ev)   { this.state.selCategory   = ev.target.value; }
    onDateFrom(ev)      { this.state.dateFrom      = ev.target.value; }
    onDateTo(ev)        { this.state.dateTo        = ev.target.value; }
    onActiveTime(ev)    { this.state.activeTime    = ev.target.value; }
    onDiscountType(ev)  { this.state.discountType  = ev.target.value; }
    onDiscountValue(ev) { this.state.discountValue = ev.target.value; }
    onPurchaseLimit(ev) { this.state.purchaseLimit = ev.target.value; }

    onSelProducts(ev) {
        this.state.selProducts = [...ev.target.selectedOptions].map(o => parseInt(o.value));
    }

    async onCreateOffer() {
        this.state.errorMsg = "";
        this.state.successMsg = "";

        if (!this.state.offerName.trim())
            return (this.state.errorMsg = "Offer Name is required.");
        if (!this.state.dateFrom || !this.state.dateTo)
            return (this.state.errorMsg = "Both dates are required.");
        if (this.state.dateFrom > this.state.dateTo)
            return (this.state.errorMsg = "From Date must be before To Date.");
        if (parseFloat(this.state.discountValue) <= 0)
            return (this.state.errorMsg = "Discount Value must be > 0.");
        if (this.state.selProducts.length === 0 && !this.state.selCategory)
            return (this.state.errorMsg = "Select at least one Product or Category.");
        if (this.state.offerType === "coupon" && !this.state.couponCode.trim())
            return (this.state.errorMsg = "Coupon Code is required for Coupon type.");

        const [h, m] = this.state.activeTime.split(":").map(Number);
        this.state.loading = true;
        try {
            await this.orm.create("pos.special.offer", [{
                name:           this.state.offerName.trim(),
                offer_type:     this.state.offerType,
                coupon_code:    this.state.couponCode.trim(),
                product_ids:    [[6, 0, this.state.selProducts]],
                category_ids:   this.state.selCategory
                    ? [[6, 0, [parseInt(this.state.selCategory)]]]
                    : [[6, 0, []]],
                date_from:      this.state.dateFrom,
                date_to:        this.state.dateTo,
                active_time:    h + (m || 0) / 60.0,
                discount_type:  this.state.discountType,
                discount_value: parseFloat(this.state.discountValue),
                purchase_limit: parseInt(this.state.purchaseLimit) || 0,
                active:         true,
            }]);
            await this.offerService.refresh();
            this.state.successMsg = `✅ Offer "${this.state.offerName}" created successfully!`;
            this.state.offerName = "";
            this.state.couponCode = "";
            this.state.selProducts = [];
            this.state.selCategory = "";
        } catch (e) {
            this.state.errorMsg = "Failed to save offer. Check console for details.";
            console.error("[SpecialOffer]", e);
        } finally {
            this.state.loading = false;
        }
    }
}
