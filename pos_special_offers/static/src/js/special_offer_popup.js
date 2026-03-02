/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class SpecialOfferPopup extends Component {
    static template = "pos_special_offers.SpecialOfferPopup";
    static props = { close: Function };

    setup() {
        this.pos = usePos();
        this.offerService = useService("special_offer_service");
        this.state = useState({
            couponInput: "",
            appliedMsg:  "",
            errorMsg:    "",
            refreshing:  false,
        });
    }

    // ── Refresh ─────────────────────────────────────────────────────────────
    async onRefresh() {
        this.state.refreshing = true;
        this.state.appliedMsg = "";
        this.state.errorMsg   = "";
        try {
            await this.offerService.refresh();
        } finally {
            this.state.refreshing = false;
        }
    }

    // ── Time check (client-side browser local time) ─────────────────────────
    isTimeActive(offer) {
        if (!offer.active_time || offer.active_time === 0) return true;
        const now = new Date();
        const nowFloat = now.getHours() + now.getMinutes() / 60.0;
        return nowFloat >= offer.active_time;
    }

    get activeOffers() {
        return this.offerService.getActiveOffers()
            .filter(o => o.offer_type === "flat_discount" && this.isTimeActive(o));
    }

    // ── Order access ─────────────────────────────────────────────────────────
    get currentOrder() {
        const p = this.pos;
        return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null;
    }

    getOrderLines(order) {
        if (!order) return [];
        if (Array.isArray(order.lines) && order.lines.length > 0)      return order.lines;
        if (typeof order.get_orderlines === "function")                 return order.get_orderlines();
        if (Array.isArray(order.orderlines))                            return order.orderlines;
        if (order.orderlines?.models)                                   return order.orderlines.models;
        return [];
    }

    getProductId(line) {
        if (line.product_id?.id)                            return line.product_id.id;
        if (typeof line.get_product === "function")         return line.get_product()?.id;
        if (line.product?.id)                               return line.product.id;
        if (typeof line.product_id === "number")            return line.product_id;
        return null;
    }

    getCategoryIds(line) {
        const product = line.product_id ?? line.product ?? line.get_product?.();
        if (!product) return [];
        const cats = product.pos_categ_ids ?? product.pos_categ_id ?? [];
        if (Array.isArray(cats)) return cats.map(c => (typeof c === "object" ? c.id : c));
        return typeof cats === "number" ? [cats] : [];
    }

    applyDiscount(line, offer) {
        try {
            if (offer.discount_type === "percentage") {
                if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
                if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
            } else {
                if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
                if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
                if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
            }
        } catch (e) {
            console.error("[SpecialOffer] applyDiscount error:", e);
        }
        return false;
    }

    applyOffer(offer) {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";

        const order = this.currentOrder;
        if (!order) { this.state.errorMsg = "No active order found."; return; }

        const lines = this.getOrderLines(order);
        if (!lines || lines.length === 0) {
            this.state.errorMsg = "Please add products to the order first.";
            return;
        }

        const noFilter = offer.product_ids.length === 0 && offer.category_ids.length === 0;
        let applied = 0;

        for (const line of lines) {
            const productId    = this.getProductId(line);
            const catIds       = this.getCategoryIds(line);
            const matchProduct  = productId && offer.product_ids.includes(productId);
            const matchCategory = catIds.some(cid => offer.category_ids.includes(cid));

            if (noFilter || matchProduct || matchCategory) {
                if (this.applyDiscount(line, offer)) applied++;
            }
        }

        if (applied > 0) {
            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
        } else {
            this.state.errorMsg = `"${offer.name}" has no matching products in this order.`;
        }
    }

    applyCoupon() {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";
        const code = this.state.couponInput.trim();
        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }

        const offer = this.offerService.getActiveOffers().find(
            o => o.offer_type === "coupon" &&
                 this.isTimeActive(o) &&
                 o.coupon_code.toLowerCase() === code.toLowerCase()
        );
        if (!offer) { this.state.errorMsg = `Coupon "${code}" is invalid or expired.`; return; }
        this.applyOffer(offer);
        this.state.couponInput = "";
    }

    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
}
