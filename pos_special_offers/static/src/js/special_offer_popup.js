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

    get allFlatOffers() {
        return this.offerService.getActiveOffers()
            .filter(o => o.offer_type === "flat_discount");
    }

    // Returns a human-readable scope label for an offer
    offerScope(offer) {
        if (offer.all_products)   return "All products";
        if (offer.all_categories) return "All categories";
        if (offer.product_ids.length > 0 && offer.category_ids.length > 0)
            return "Selected products & categories";
        if (offer.product_ids.length > 0)   return "Selected products only";
        if (offer.category_ids.length > 0)  return "Selected categories only";
        return "All products";  // fallback: nothing selected = all
    }

    get currentOrder() {
        const p = this.pos;
        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
        catch(e) { return null; }
    }

    getOrderLines(order) {
        if (!order) return [];
        try {
            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
            if (typeof order.get_orderlines === "function")            return order.get_orderlines() || [];
            if (Array.isArray(order.orderlines))                       return order.orderlines;
            if (order.orderlines?.models)                              return order.orderlines.models;
        } catch(e) {}
        return [];
    }

    getProductId(line) {
        try {
            if (line.product_id?.id)                    return line.product_id.id;
            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
            if (line.product?.id)                       return line.product.id;
            if (typeof line.product_id === "number")    return line.product_id;
        } catch(e) {}
        return null;
    }

    getProductCategoryIds(line) {
        try {
            const product = line.product_id ?? line.product ?? line.get_product?.();
            if (!product) return [];
            const cat = product.categ_id ?? product.category_id;
            if (!cat) return [];
            const catId = typeof cat === "object" ? cat.id : cat;
            return catId ? [catId] : [];
        } catch(e) { return []; }
    }

    lineMatchesOffer(line, offer) {
        // all_products = apply to every line
        if (offer.all_products) return true;

        const pid    = this.getProductId(line);
        const catIds = this.getProductCategoryIds(line);

        // all_categories = match any category
        if (offer.all_categories) return true;

        // specific product match
        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid)) return true;

        // specific category match
        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;

        // nothing selected at all = apply to everything (fallback)
        if (offer.product_ids.length === 0 && offer.category_ids.length === 0) return true;

        return false;
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

        const order = this.currentOrder;
        if (!order) { this.state.errorMsg = "No active order found."; return; }

        const lines = this.getOrderLines(order);
        if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }

        let applied = 0;
        for (const line of lines) {
            if (this.lineMatchesOffer(line, offer)) {
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
            o => o.offer_type === "coupon" &&
                 o.coupon_code.toLowerCase() === code.toLowerCase()
        );
        if (!offer) { this.state.errorMsg = `Coupon "${code}" is invalid or expired.`; return; }
        this.applyOffer(offer);
        this.state.couponInput = "";
    }

    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
}
