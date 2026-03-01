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
        this.state = useState({
            couponInput: "",
            appliedMsg:  "",
            errorMsg:    "",
        });
    }

    get activeOffers() {
        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    }

    get currentOrder() {
        try {
            if (this.pos.get_order)      return this.pos.get_order();
            if (this.pos.selectedOrder)  return this.pos.selectedOrder;
            if (this.pos.currentOrder)   return this.pos.currentOrder;
            if (this.pos.orders?.length) return this.pos.orders[0];
        } catch (e) {}
        return null;
    }

    getOrderLines(order) {
        try {
            if (typeof order.get_orderlines === "function") return order.get_orderlines();
            if (typeof order.getOrderlines  === "function") return order.getOrderlines();
            if (Array.isArray(order.orderlines))            return order.orderlines;
            if (order.orderlines?.models)                   return order.orderlines.models;
            const lines = Object.values(order).find(
                v => Array.isArray(v) && v.length > 0 && v[0]?.product_id !== undefined
            );
            if (lines) return lines;
        } catch (e) {}
        return [];
    }

    getProductId(line) {
        try {
            if (typeof line.get_product === "function") return line.get_product()?.id;
            if (line.product_id?.id)  return line.product_id.id;
            if (line.product?.id)     return line.product.id;
            if (line.product_id)      return line.product_id;
        } catch (e) {}
        return null;
    }

    getCategoryIds(line) {
        try {
            const product = typeof line.get_product === "function"
                ? line.get_product()
                : (line.product || line.product_id);
            if (!product) return [];
            return product.pos_categ_ids || product.pos_categ_id || [];
        } catch (e) { return []; }
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
        if (!order) {
            this.state.errorMsg = "No active order found. Please start an order first.";
            return;
        }

        const lines = this.getOrderLines(order);
        if (!lines || lines.length === 0) {
            this.state.errorMsg = "Please add products to the order before applying an offer.";
            return;
        }

        const noFilter = offer.product_ids.length === 0 && offer.category_ids.length === 0;
        let applied = 0;

        for (const line of lines) {
            const productId     = this.getProductId(line);
            const catIds        = this.getCategoryIds(line);
            const matchProduct  = productId && offer.product_ids.includes(productId);
            const matchCategory = catIds.some(cid => offer.category_ids.includes(cid));

            if (noFilter || matchProduct || matchCategory) {
                if (this.applyDiscount(line, offer)) applied++;
            }
        }

        if (applied > 0) {
            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
        } else {
            this.state.errorMsg = `No matching products in the order for "${offer.name}".`;
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
