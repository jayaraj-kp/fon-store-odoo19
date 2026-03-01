/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class SpecialOfferPopup extends Component {
    static template = "pos_special_offers.SpecialOfferPopup";
    static props = {
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.offerService = useService("special_offer_service");
        this.notification = useService("notification");
        this.state = useState({
            couponInput: "",
            appliedMsg: "",
            errorMsg: "",
        });
    }

    get activeOffers() {
        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    }

    get couponOffers() {
        return this.offerService.getActiveOffers().filter(o => o.offer_type === "coupon");
    }

    get currentOrder() {
        return this.pos.get_order?.() || this.pos.selectedOrder || null;
    }

    // Apply a flat discount offer to the current order
    applyOffer(offer) {
        this.state.errorMsg = "";
        this.state.appliedMsg = "";

        const order = this.currentOrder;
        if (!order) {
            this.state.errorMsg = "No active order found.";
            return;
        }

        const lines = order.get_orderlines?.() || order.orderlines || [];
        if (!lines.length) {
            this.state.errorMsg = "Add products to the order first.";
            return;
        }

        let applied = 0;
        for (const line of lines) {
            const productId = line.get_product?.()?.id || line.product?.id;
            const categoryIds = line.get_product?.()?.pos_categ_ids || line.product?.pos_categ_ids || [];

            const matchProduct = offer.product_ids.includes(productId);
            const matchCategory = categoryIds.some(cid => offer.category_ids.includes(cid));

            if (matchProduct || matchCategory || (offer.product_ids.length === 0 && offer.category_ids.length === 0)) {
                if (offer.discount_type === "percentage") {
                    line.set_discount?.(offer.discount_value);
                } else {
                    // Fixed price — set custom price
                    line.set_unit_price?.(offer.discount_value);
                }
                applied++;
            }
        }

        if (applied > 0) {
            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
        } else {
            this.state.errorMsg = `No matching products in the order for "${offer.name}".`;
        }
    }

    // Apply coupon code
    applyCoupon() {
        this.state.errorMsg = "";
        this.state.appliedMsg = "";

        const code = this.state.couponInput.trim();
        if (!code) {
            this.state.errorMsg = "Please enter a coupon code.";
            return;
        }

        const offer = this.offerService.getActiveOffers().find(
            o => o.offer_type === "coupon" &&
                 o.coupon_code.toLowerCase() === code.toLowerCase()
        );

        if (!offer) {
            this.state.errorMsg = `Coupon code "${code}" is not valid or has expired.`;
            return;
        }

        this.applyOffer(offer);
        this.state.couponInput = "";
    }

    onCouponInput(ev) {
        this.state.couponInput = ev.target.value;
    }
}
