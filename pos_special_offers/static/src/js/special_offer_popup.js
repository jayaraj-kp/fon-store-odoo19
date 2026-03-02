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

    async onRefresh() {
        this.state.refreshing = true;
        this.state.appliedMsg = "";
        this.state.errorMsg   = "";
        try {
            await this.offerService.refresh();
        } catch(e) {
            this.state.errorMsg = "Refresh failed. Check your connection.";
        } finally {
            this.state.refreshing = false;
        }
    }

    isTimeActive(offer) {
        if (!offer.active_time || offer.active_time === 0) return true;
        const now = new Date();
        return (now.getHours() + now.getMinutes() / 60.0) >= offer.active_time;
    }

    get allFlatOffers() {
        return this.offerService.getActiveOffers()
            .filter(o => o.offer_type === "flat_discount");
    }

    get currentOrder() {
        const p = this.pos;
        try {
            return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null;
        } catch(e) { return null; }
    }

    getOrderLines(order) {
        if (!order) return [];
        try {
            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
            if (typeof order.get_orderlines === "function")            return order.get_orderlines() || [];
            if (Array.isArray(order.orderlines))                       return order.orderlines;
            if (order.orderlines?.models)                              return order.orderlines.models;
        } catch(e) { console.warn("[SpecialOffer] getOrderLines error:", e); }
        return [];
    }

    getProductId(line) {
        try {
            if (line.product_id?.id)                        return line.product_id.id;
            if (typeof line.get_product === "function")     return line.get_product()?.id ?? null;
            if (line.product?.id)                           return line.product.id;
            if (typeof line.product_id === "number")        return line.product_id;
        } catch(e) {}
        return null;
    }

    getCategoryIds(line) {
        try {
            const product = line.product_id ?? line.product ?? line.get_product?.();
            if (!product) return [];
            const cats = product.pos_categ_ids ?? product.pos_categ_id ?? [];
            if (Array.isArray(cats)) return cats.map(c => typeof c === "object" ? c.id : c).filter(Boolean);
            return typeof cats === "number" ? [cats] : [];
        } catch(e) { return []; }
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
        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
        return false;
    }

    applyOffer(offer) {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";

        if (!this.isTimeActive(offer)) {
            const h = Math.floor(offer.active_time);
            const m = String(Math.round((offer.active_time - h) * 60)).padStart(2, "0");
            this.state.errorMsg = `"${offer.name}" is only active from ${String(h).padStart(2,"0")}:${m} onwards.`;
            return;
        }

        const order = this.currentOrder;
        if (!order) { this.state.errorMsg = "No active order found."; return; }

        const lines = this.getOrderLines(order);
        if (!lines.length) {
            this.state.errorMsg = "Please add products to the order first.";
            return;
        }

        const noFilter = offer.product_ids.length === 0 && offer.category_ids.length === 0;
        let applied = 0;
        for (const line of lines) {
            const pid  = this.getProductId(line);
            const cats = this.getCategoryIds(line);
            if (noFilter || (pid && offer.product_ids.includes(pid)) || cats.some(c => offer.category_ids.includes(c))) {
                if (this.applyDiscount(line, offer)) applied++;
            }
        }

        if (applied > 0) {
            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
        } else {
            this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
        }
    }

    applyCoupon() {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";
        const code = this.state.couponInput.trim();
        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }

        const offer = this.offerService.getActiveOffers().find(
            o => o.offer_type === "coupon" && o.coupon_code.toLowerCase() === code.toLowerCase()
        );
        if (!offer) { this.state.errorMsg = `Coupon "${code}" is invalid or expired.`; return; }

        if (!this.isTimeActive(offer)) {
            const h = Math.floor(offer.active_time);
            const m = String(Math.round((offer.active_time - h) * 60)).padStart(2, "0");
            this.state.errorMsg = `This coupon is only active from ${String(h).padStart(2,"0")}:${m} onwards.`;
            return;
        }
        this.applyOffer(offer);
        this.state.couponInput = "";
    }

    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
}
