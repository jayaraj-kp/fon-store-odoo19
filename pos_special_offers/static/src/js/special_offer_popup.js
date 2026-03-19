///////** @odoo-module **/
//////import { Component, useState } from "@odoo/owl";
//////import { useService } from "@web/core/utils/hooks";
//////import { usePos } from "@point_of_sale/app/hooks/pos_hook";
//////
//////export class SpecialOfferPopup extends Component {
//////    static template = "pos_special_offers.SpecialOfferPopup";
//////    static props = { close: Function };
//////
//////    setup() {
//////        this.pos = usePos();
//////        this.offerService = useService("special_offer_service");
//////        this.orm = useService("orm");
//////        this.state = useState({
//////            couponInput: "",
//////            appliedMsg:  "",
//////            errorMsg:    "",
//////            refreshing:  false,
//////        });
//////    }
//////
//////    async onRefresh() {
//////        this.state.refreshing = true;
//////        this.state.appliedMsg = "";
//////        this.state.errorMsg   = "";
//////        try {
//////            await this.offerService.refresh();
//////        } catch(e) {
//////            this.state.errorMsg = "Refresh failed. Check your connection.";
//////        } finally {
//////            this.state.refreshing = false;
//////        }
//////    }
//////
//////    get allFlatOffers() {
//////        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
//////    }
//////
//////    get currentOrder() {
//////        const p = this.pos;
//////        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
//////        catch(e) { return null; }
//////    }
//////
//////    getOrderLines(order) {
//////        if (!order) return [];
//////        try {
//////            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
//////            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
//////            if (Array.isArray(order.orderlines))            return order.orderlines;
//////            if (order.orderlines?.models)                   return order.orderlines.models;
//////        } catch(e) {}
//////        return [];
//////    }
//////
//////    getProductId(line) {
//////        try {
//////            if (line.product_id?.id)                    return line.product_id.id;
//////            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
//////            if (line.product?.id)                       return line.product.id;
//////            if (typeof line.product_id === "number")    return line.product_id;
//////        } catch(e) {}
//////        return null;
//////    }
//////
//////    getProductCategoryIds(line) {
//////        try {
//////            const product = line.product_id ?? line.product ?? line.get_product?.();
//////            if (!product) return [];
//////            const cat = product.categ_id ?? product.category_id;
//////            if (!cat) return [];
//////            const catId = typeof cat === "object" ? cat.id : cat;
//////            return catId ? [catId] : [];
//////        } catch(e) { return []; }
//////    }
//////
//////    lineMatchesOffer(line, offer) {
//////        if (offer.all_products)   return true;
//////        if (offer.all_categories) return true;
//////        const pid    = this.getProductId(line);
//////        const catIds = this.getProductCategoryIds(line);
//////        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))           return true;
//////        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
//////        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
//////        return false;
//////    }
//////
//////    applyDiscount(line, offer) {
//////        try {
//////            if (offer.discount_type === "percentage") {
//////                if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
//////                if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
//////            } else {
//////                if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
//////                if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
//////                if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
//////            }
//////        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
//////        return false;
//////    }
//////
//////    applyOffer(offer) {
//////        this.state.errorMsg   = "";
//////        this.state.appliedMsg = "";
//////        const order = this.currentOrder;
//////        if (!order) { this.state.errorMsg = "No active order found."; return; }
//////        const lines = this.getOrderLines(order);
//////        if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
//////        let applied = 0;
//////        for (const line of lines) {
//////            if (this.lineMatchesOffer(line, offer)) {
//////                if (this.applyDiscount(line, offer)) applied++;
//////            }
//////        }
//////        if (applied > 0) {
//////            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
//////        } else {
//////            this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
//////        }
//////    }
//////
//////    async applyCoupon() {
//////        this.state.errorMsg   = "";
//////        this.state.appliedMsg = "";
//////        const code = this.state.couponInput.trim();
//////        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
//////
//////        const allOffers = this.offerService.getActiveOffers();
//////        let matchedOffer = null;
//////        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
//////
//////        for (const offer of allOffers) {
//////            if (offer.offer_type !== "coupon") continue;
//////
//////            // 1. Check generated codes first
//////            if (offer.generated_codes && offer.generated_codes.length > 0) {
//////                const found = offer.generated_codes.find(
//////                    c => c.code.toLowerCase() === code.toLowerCase()
//////                );
//////                if (found) {
//////                    matchedOffer  = offer;
//////                    matchedCoupon = found;
//////                    break;
//////                }
//////            }
//////
//////            // 2. Fall back to single coupon_code
//////            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
//////                matchedOffer = offer;
//////                break;
//////            }
//////        }
//////
//////        if (!matchedOffer) {
//////            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
//////            return;
//////        }
//////
//////        // Apply the discount
//////        this.applyOffer(matchedOffer);
//////
//////        // Mark generated coupon as used on the server
//////        if (matchedCoupon && this.state.appliedMsg) {
//////            try {
//////                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
//////                // Remove from local offer list so it can't be reused in this session
//////                if (matchedCoupon.single_use) {
//////                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
//////                        c => c.id !== matchedCoupon.id
//////                    );
//////                }
//////            } catch(e) {
//////                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
//////            }
//////        }
//////
//////        this.state.couponInput = "";
//////    }
//////
//////    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
//////}
/////** @odoo-module **/
////import { Component, useState } from "@odoo/owl";
////import { useService } from "@web/core/utils/hooks";
////import { usePos } from "@point_of_sale/app/hooks/pos_hook";
////
////export class SpecialOfferPopup extends Component {
////    static template = "pos_special_offers.SpecialOfferPopup";
////    static props = { close: Function };
////
////    setup() {
////        this.pos = usePos();
////        this.offerService = useService("special_offer_service");
////        this.orm = useService("orm");
////        this.state = useState({
////            couponInput: "",
////            appliedMsg:  "",
////            errorMsg:    "",
////            refreshing:  false,
////        });
////    }
////
////    async onRefresh() {
////        this.state.refreshing = true;
////        this.state.appliedMsg = "";
////        this.state.errorMsg   = "";
////        try {
////            await this.offerService.refresh();
////        } catch(e) {
////            this.state.errorMsg = "Refresh failed. Check your connection.";
////        } finally {
////            this.state.refreshing = false;
////        }
////    }
////
////    get allFlatOffers() {
////        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
////    }
////
////    get currentOrder() {
////        const p = this.pos;
////        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
////        catch(e) { return null; }
////    }
////
////    getOrderLines(order) {
////        if (!order) return [];
////        try {
////            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
////            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
////            if (Array.isArray(order.orderlines))            return order.orderlines;
////            if (order.orderlines?.models)                   return order.orderlines.models;
////        } catch(e) {}
////        return [];
////    }
////
////    getProductId(line) {
////        try {
////            if (line.product_id?.id)                    return line.product_id.id;
////            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
////            if (line.product?.id)                       return line.product.id;
////            if (typeof line.product_id === "number")    return line.product_id;
////        } catch(e) {}
////        return null;
////    }
////
////    getProductCategoryIds(line) {
////        try {
////            const product = line.product_id ?? line.product ?? line.get_product?.();
////            if (!product) return [];
////            const cat = product.categ_id ?? product.category_id;
////            if (!cat) return [];
////            const catId = typeof cat === "object" ? cat.id : cat;
////            return catId ? [catId] : [];
////        } catch(e) { return []; }
////    }
////
////    lineMatchesOffer(line, offer) {
////        if (offer.all_products)   return true;
////        if (offer.all_categories) return true;
////        const pid    = this.getProductId(line);
////        const catIds = this.getProductCategoryIds(line);
////        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))            return true;
////        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
////        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
////        return false;
////    }
////
////    /**
////     * FIXED: For 'fixed' discount type, we now SUBTRACT the discount value
////     * from the current unit price instead of replacing it.
////     * For 'percentage', we apply it as a discount % (unchanged).
////     */
////    applyDiscount(line, offer) {
////        try {
////            if (offer.discount_type === "percentage") {
////                // Percentage discount — set the % discount field
////                if (typeof line.set_discount === "function") {
////                    line.set_discount(offer.discount_value);
////                    return true;
////                }
////                if ("discount" in line) {
////                    line.discount = offer.discount_value;
////                    return true;
////                }
////            } else {
////                // Fixed amount discount — SUBTRACT from current price
////                let currentPrice = null;
////
////                // Get current unit price
////                if (typeof line.get_unit_price === "function") {
////                    currentPrice = line.get_unit_price();
////                } else if (typeof line.getUnitPrice === "function") {
////                    currentPrice = line.getUnitPrice();
////                } else if (line.price_unit !== undefined) {
////                    currentPrice = line.price_unit;
////                } else if (line.price !== undefined) {
////                    currentPrice = line.price;
////                }
////
////                if (currentPrice === null || currentPrice === undefined) {
////                    console.warn("[SpecialOffer] Could not get current price for line");
////                    return false;
////                }
////
////                // Calculate new price after deducting fixed amount (minimum 0)
////                const newPrice = Math.max(0, currentPrice - offer.discount_value);
////
////                if (typeof line.set_unit_price === "function") {
////                    line.set_unit_price(newPrice);
////                    return true;
////                }
////                if (typeof line.setUnitPrice === "function") {
////                    line.setUnitPrice(newPrice);
////                    return true;
////                }
////                if ("price_unit" in line) {
////                    line.price_unit = newPrice;
////                    return true;
////                }
////            }
////        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
////        return false;
////    }
////
////    getSelectedLine(order) {
////        try {
////            // Odoo 17/18/19 POS — various ways to get the selected/highlighted line
////            if (typeof order.get_selected_orderline === "function") return order.get_selected_orderline();
////            if (typeof order.getSelectedOrderline  === "function") return order.getSelectedOrderline();
////            if (order.selected_orderline)  return order.selected_orderline;
////            if (order.selectedOrderline)   return order.selectedOrderline;
////        } catch(e) {}
////        return null;
////    }
////
////    /**
////     * For FLAT DISCOUNT offers: apply to all matching lines (existing behaviour).
////     * For COUPON offers: apply only to the currently selected order line.
////     */
////    applyOffer(offer, couponMode = false) {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const order = this.currentOrder;
////        if (!order) { this.state.errorMsg = "No active order found."; return; }
////
////        if (couponMode) {
////            // ── Coupon: apply only to the selected line ───────────────────────
////            const line = this.getSelectedLine(order);
////            if (!line) {
////                this.state.errorMsg = "Please select a product line in the order first.";
////                return;
////            }
////            if (!this.lineMatchesOffer(line, offer)) {
////                const lines = this.getOrderLines(order);
////                if (!lines.length) {
////                    this.state.errorMsg = "Please add products to the order first.";
////                    return;
////                }
////                // Offer doesn't match the selected line — still apply (coupon applies regardless of product scope when used manually)
////            }
////            if (this.applyDiscount(line, offer)) {
////                this.state.appliedMsg = `✅ "${offer.name}" applied to selected product!`;
////            } else {
////                this.state.errorMsg = `Could not apply "${offer.name}" to the selected line.`;
////            }
////        } else {
////            // ── Flat discount: apply to ALL matching lines (unchanged) ────────
////            const lines = this.getOrderLines(order);
////            if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
////            let applied = 0;
////            for (const line of lines) {
////                if (this.lineMatchesOffer(line, offer)) {
////                    if (this.applyDiscount(line, offer)) applied++;
////                }
////            }
////            if (applied > 0) {
////                this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
////            } else {
////                this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
////            }
////        }
////    }
////
////    async applyCoupon() {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const code = this.state.couponInput.trim();
////        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
////
////        const allOffers = this.offerService.getActiveOffers();
////        let matchedOffer = null;
////        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
////
////        for (const offer of allOffers) {
////            if (offer.offer_type !== "coupon") continue;
////
////            // 1. Check generated codes first
////            if (offer.generated_codes && offer.generated_codes.length > 0) {
////                const found = offer.generated_codes.find(
////                    c => c.code.toLowerCase() === code.toLowerCase()
////                );
////                if (found) {
////                    matchedOffer  = offer;
////                    matchedCoupon = found;
////                    break;
////                }
////            }
////
////            // 2. Fall back to single coupon_code
////            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
////                matchedOffer = offer;
////                break;
////            }
////        }
////
////        if (!matchedOffer) {
////            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
////            return;
////        }
////
////        // Apply the discount only to the selected line (coupon mode)
////        this.applyOffer(matchedOffer, true);
////
////        // Mark generated coupon as used on the server
////        if (matchedCoupon && this.state.appliedMsg) {
////            try {
////                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
////                // Remove from local offer list so it can't be reused in this session
////                if (matchedCoupon.single_use) {
////                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
////                        c => c.id !== matchedCoupon.id
////                    );
////                }
////            } catch(e) {
////                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
////            }
////        }
////
////        this.state.couponInput = "";
////    }
////
////    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
////}
/////** @odoo-module **/
////import { Component, useState } from "@odoo/owl";
////import { useService } from "@web/core/utils/hooks";
////import { usePos } from "@point_of_sale/app/hooks/pos_hook";
////
////export class SpecialOfferPopup extends Component {
////    static template = "pos_special_offers.SpecialOfferPopup";
////    static props = { close: Function };
////
////    setup() {
////        this.pos = usePos();
////        this.offerService = useService("special_offer_service");
////        this.orm = useService("orm");
////        this.state = useState({
////            couponInput: "",
////            appliedMsg:  "",
////            errorMsg:    "",
////            refreshing:  false,
////        });
////    }
////
////    async onRefresh() {
////        this.state.refreshing = true;
////        this.state.appliedMsg = "";
////        this.state.errorMsg   = "";
////        try {
////            await this.offerService.refresh();
////        } catch(e) {
////            this.state.errorMsg = "Refresh failed. Check your connection.";
////        } finally {
////            this.state.refreshing = false;
////        }
////    }
////
////    get allFlatOffers() {
////        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
////    }
////
////    get currentOrder() {
////        const p = this.pos;
////        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
////        catch(e) { return null; }
////    }
////
////    getOrderLines(order) {
////        if (!order) return [];
////        try {
////            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
////            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
////            if (Array.isArray(order.orderlines))            return order.orderlines;
////            if (order.orderlines?.models)                   return order.orderlines.models;
////        } catch(e) {}
////        return [];
////    }
////
////    getProductId(line) {
////        try {
////            if (line.product_id?.id)                    return line.product_id.id;
////            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
////            if (line.product?.id)                       return line.product.id;
////            if (typeof line.product_id === "number")    return line.product_id;
////        } catch(e) {}
////        return null;
////    }
////
////    getProductCategoryIds(line) {
////        try {
////            const product = line.product_id ?? line.product ?? line.get_product?.();
////            if (!product) return [];
////            const cat = product.categ_id ?? product.category_id;
////            if (!cat) return [];
////            const catId = typeof cat === "object" ? cat.id : cat;
////            return catId ? [catId] : [];
////        } catch(e) { return []; }
////    }
////
////    lineMatchesOffer(line, offer) {
////        if (offer.all_products)   return true;
////        if (offer.all_categories) return true;
////        const pid    = this.getProductId(line);
////        const catIds = this.getProductCategoryIds(line);
////        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))           return true;
////        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
////        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
////        return false;
////    }
////
////    applyDiscount(line, offer) {
////        try {
////            if (offer.discount_type === "percentage") {
////                if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
////                if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
////            } else {
////                if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
////                if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
////                if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
////            }
////        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
////        return false;
////    }
////
////    applyOffer(offer) {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const order = this.currentOrder;
////        if (!order) { this.state.errorMsg = "No active order found."; return; }
////        const lines = this.getOrderLines(order);
////        if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
////        let applied = 0;
////        for (const line of lines) {
////            if (this.lineMatchesOffer(line, offer)) {
////                if (this.applyDiscount(line, offer)) applied++;
////            }
////        }
////        if (applied > 0) {
////            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
////        } else {
////            this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
////        }
////    }
////
////    async applyCoupon() {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const code = this.state.couponInput.trim();
////        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
////
////        const allOffers = this.offerService.getActiveOffers();
////        let matchedOffer = null;
////        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
////
////        for (const offer of allOffers) {
////            if (offer.offer_type !== "coupon") continue;
////
////            // 1. Check generated codes first
////            if (offer.generated_codes && offer.generated_codes.length > 0) {
////                const found = offer.generated_codes.find(
////                    c => c.code.toLowerCase() === code.toLowerCase()
////                );
////                if (found) {
////                    matchedOffer  = offer;
////                    matchedCoupon = found;
////                    break;
////                }
////            }
////
////            // 2. Fall back to single coupon_code
////            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
////                matchedOffer = offer;
////                break;
////            }
////        }
////
////        if (!matchedOffer) {
////            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
////            return;
////        }
////
////        // Apply the discount
////        this.applyOffer(matchedOffer);
////
////        // Mark generated coupon as used on the server
////        if (matchedCoupon && this.state.appliedMsg) {
////            try {
////                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
////                // Remove from local offer list so it can't be reused in this session
////                if (matchedCoupon.single_use) {
////                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
////                        c => c.id !== matchedCoupon.id
////                    );
////                }
////            } catch(e) {
////                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
////            }
////        }
////
////        this.state.couponInput = "";
////    }
////
////    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
////}
///** @odoo-module **/
//import { Component, useState } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { usePos } from "@point_of_sale/app/hooks/pos_hook";
//
//export class SpecialOfferPopup extends Component {
//    static template = "pos_special_offers.SpecialOfferPopup";
//    static props = { close: Function };
//
//    setup() {
//        this.pos = usePos();
//        this.offerService = useService("special_offer_service");
//        this.orm = useService("orm");
//        this.state = useState({
//            couponInput: "",
//            appliedMsg:  "",
//            errorMsg:    "",
//            refreshing:  false,
//        });
//    }
//
//    async onRefresh() {
//        this.state.refreshing = true;
//        this.state.appliedMsg = "";
//        this.state.errorMsg   = "";
//        try {
//            await this.offerService.refresh();
//        } catch(e) {
//            this.state.errorMsg = "Refresh failed. Check your connection.";
//        } finally {
//            this.state.refreshing = false;
//        }
//    }
//
//    get allFlatOffers() {
//        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
//    }
//
//    get currentOrder() {
//        const p = this.pos;
//        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
//        catch(e) { return null; }
//    }
//
//    getOrderLines(order) {
//        if (!order) return [];
//        try {
//            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
//            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
//            if (Array.isArray(order.orderlines))            return order.orderlines;
//            if (order.orderlines?.models)                   return order.orderlines.models;
//        } catch(e) {}
//        return [];
//    }
//
//    getProductId(line) {
//        try {
//            if (line.product_id?.id)                    return line.product_id.id;
//            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
//            if (line.product?.id)                       return line.product.id;
//            if (typeof line.product_id === "number")    return line.product_id;
//        } catch(e) {}
//        return null;
//    }
//
//    getProductCategoryIds(line) {
//        try {
//            const product = line.product_id ?? line.product ?? line.get_product?.();
//            if (!product) return [];
//            const cat = product.categ_id ?? product.category_id;
//            if (!cat) return [];
//            const catId = typeof cat === "object" ? cat.id : cat;
//            return catId ? [catId] : [];
//        } catch(e) { return []; }
//    }
//
//    lineMatchesOffer(line, offer) {
//        if (offer.all_products)   return true;
//        if (offer.all_categories) return true;
//        const pid    = this.getProductId(line);
//        const catIds = this.getProductCategoryIds(line);
//        // Check specific product list
//        if (offer.product_ids && offer.product_ids.length > 0) {
//            if (pid && offer.product_ids.includes(pid)) return true;
//        }
//        // Check specific category list
//        if (offer.category_ids && offer.category_ids.length > 0) {
//            if (catIds.some(c => offer.category_ids.includes(c))) return true;
//        }
//        // FIX: Do NOT fall back to "match all" when both lists are empty.
//        // An offer with no all_products/all_categories and no specific products/categories
//        // should NOT match anything — prevents applying to unintended products.
//        return false;
//    }
//
//    /**
//     * FIXED: For 'fixed' discount type, we now SUBTRACT the discount value
//     * from the current unit price instead of replacing it.
//     * For 'percentage', we apply it as a discount % (unchanged).
//     */
//    applyDiscount(line, offer) {
//        try {
//            if (offer.discount_type === "percentage") {
//                // Percentage discount — set the % discount field
//                if (typeof line.set_discount === "function") {
//                    line.set_discount(offer.discount_value);
//                    return true;
//                }
//                if ("discount" in line) {
//                    line.discount = offer.discount_value;
//                    return true;
//                }
//            } else {
//                // Fixed amount discount — SUBTRACT from current price
//                let currentPrice = null;
//
//                // Get current unit price
//                if (typeof line.get_unit_price === "function") {
//                    currentPrice = line.get_unit_price();
//                } else if (typeof line.getUnitPrice === "function") {
//                    currentPrice = line.getUnitPrice();
//                } else if (line.price_unit !== undefined) {
//                    currentPrice = line.price_unit;
//                } else if (line.price !== undefined) {
//                    currentPrice = line.price;
//                }
//
//                if (currentPrice === null || currentPrice === undefined) {
//                    console.warn("[SpecialOffer] Could not get current price for line");
//                    return false;
//                }
//
//                // Calculate new price after deducting fixed amount (minimum 0)
//                const newPrice = Math.max(0, currentPrice - offer.discount_value);
//
//                if (typeof line.set_unit_price === "function") {
//                    line.set_unit_price(newPrice);
//                    return true;
//                }
//                if (typeof line.setUnitPrice === "function") {
//                    line.setUnitPrice(newPrice);
//                    return true;
//                }
//                if ("price_unit" in line) {
//                    line.price_unit = newPrice;
//                    return true;
//                }
//            }
//        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
//        return false;
//    }
//
//    getSelectedLine(order) {
//        try {
//            // Odoo 17/18/19 POS — various ways to get the selected/highlighted line
//            if (typeof order.get_selected_orderline === "function") return order.get_selected_orderline();
//            if (typeof order.getSelectedOrderline  === "function") return order.getSelectedOrderline();
//            if (order.selected_orderline)  return order.selected_orderline;
//            if (order.selectedOrderline)   return order.selectedOrderline;
//        } catch(e) {}
//        return null;
//    }
//
//    /**
//     * For FLAT DISCOUNT offers: apply to all matching lines (existing behaviour).
//     * For COUPON offers: apply only to the currently selected order line.
//     */
//    applyOffer(offer, couponMode = false) {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const order = this.currentOrder;
//        if (!order) { this.state.errorMsg = "No active order found."; return; }
//
//        if (couponMode) {
//            // ── Coupon: apply to ALL matching lines in the order ──────────────
//            // Enforces product/category scope — only lines matching the offer are discounted.
//            const lines = this.getOrderLines(order);
//            if (!lines.length) {
//                this.state.errorMsg = "Please add products to the order first.";
//                return;
//            }
//            let applied = 0;
//            for (const line of lines) {
//                if (this.lineMatchesOffer(line, offer)) {
//                    if (this.applyDiscount(line, offer)) applied++;
//                }
//            }
//            if (applied > 0) {
//                this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} matching product(s)!`;
//            } else {
//                this.state.errorMsg = `This coupon is only valid for specific products not present in this order.`;
//            }
//        } else {
//            // ── Flat discount: apply to ALL matching lines (unchanged) ────────
//            const lines = this.getOrderLines(order);
//            if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
//            let applied = 0;
//            for (const line of lines) {
//                if (this.lineMatchesOffer(line, offer)) {
//                    if (this.applyDiscount(line, offer)) applied++;
//                }
//            }
//            if (applied > 0) {
//                this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
//            } else {
//                this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
//            }
//        }
//    }
//
//    async applyCoupon() {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const code = this.state.couponInput.trim();
//        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
//
//        const allOffers = this.offerService.getActiveOffers();
//        let matchedOffer = null;
//        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
//
//        for (const offer of allOffers) {
//            if (offer.offer_type !== "coupon") continue;
//
//            // 1. Check generated codes first
//            if (offer.generated_codes && offer.generated_codes.length > 0) {
//                const found = offer.generated_codes.find(
//                    c => c.code.toLowerCase() === code.toLowerCase()
//                );
//                if (found) {
//                    matchedOffer  = offer;
//                    matchedCoupon = found;
//                    break;
//                }
//            }
//
//            // 2. Fall back to single coupon_code
//            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
//                matchedOffer = offer;
//                break;
//            }
//        }
//
//        if (!matchedOffer) {
//            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
//            return;
//        }
//
//        // Apply the discount only to the selected line (coupon mode)
//        this.applyOffer(matchedOffer, true);
//
//        // Mark generated coupon as used on the server
//        if (matchedCoupon && this.state.appliedMsg) {
//            try {
//                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
//                // Remove from local offer list so it can't be reused in this session
//                if (matchedCoupon.single_use) {
//                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
//                        c => c.id !== matchedCoupon.id
//                    );
//                }
//            } catch(e) {
//                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
//            }
//        }
//
//        this.state.couponInput = "";
//    }
//
//    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
//}

/////** @odoo-module **/
////import { Component, useState } from "@odoo/owl";
////import { useService } from "@web/core/utils/hooks";
////import { usePos } from "@point_of_sale/app/hooks/pos_hook";
////
////export class SpecialOfferPopup extends Component {
////    static template = "pos_special_offers.SpecialOfferPopup";
////    static props = { close: Function };
////
////    setup() {
////        this.pos = usePos();
////        this.offerService = useService("special_offer_service");
////        this.orm = useService("orm");
////        this.state = useState({
////            couponInput: "",
////            appliedMsg:  "",
////            errorMsg:    "",
////            refreshing:  false,
////        });
////    }
////
////    async onRefresh() {
////        this.state.refreshing = true;
////        this.state.appliedMsg = "";
////        this.state.errorMsg   = "";
////        try {
////            await this.offerService.refresh();
////        } catch(e) {
////            this.state.errorMsg = "Refresh failed. Check your connection.";
////        } finally {
////            this.state.refreshing = false;
////        }
////    }
////
////    get allFlatOffers() {
////        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
////    }
////
////    get currentOrder() {
////        const p = this.pos;
////        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
////        catch(e) { return null; }
////    }
////
////    getOrderLines(order) {
////        if (!order) return [];
////        try {
////            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
////            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
////            if (Array.isArray(order.orderlines))            return order.orderlines;
////            if (order.orderlines?.models)                   return order.orderlines.models;
////        } catch(e) {}
////        return [];
////    }
////
////    getProductId(line) {
////        try {
////            if (line.product_id?.id)                    return line.product_id.id;
////            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
////            if (line.product?.id)                       return line.product.id;
////            if (typeof line.product_id === "number")    return line.product_id;
////        } catch(e) {}
////        return null;
////    }
////
////    getProductCategoryIds(line) {
////        try {
////            const product = line.product_id ?? line.product ?? line.get_product?.();
////            if (!product) return [];
////            const cat = product.categ_id ?? product.category_id;
////            if (!cat) return [];
////            const catId = typeof cat === "object" ? cat.id : cat;
////            return catId ? [catId] : [];
////        } catch(e) { return []; }
////    }
////
////    lineMatchesOffer(line, offer) {
////        if (offer.all_products)   return true;
////        if (offer.all_categories) return true;
////        const pid    = this.getProductId(line);
////        const catIds = this.getProductCategoryIds(line);
////        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))           return true;
////        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
////        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
////        return false;
////    }
////
////    applyDiscount(line, offer) {
////        try {
////            if (offer.discount_type === "percentage") {
////                if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
////                if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
////            } else {
////                if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
////                if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
////                if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
////            }
////        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
////        return false;
////    }
////
////    applyOffer(offer) {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const order = this.currentOrder;
////        if (!order) { this.state.errorMsg = "No active order found."; return; }
////        const lines = this.getOrderLines(order);
////        if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
////        let applied = 0;
////        for (const line of lines) {
////            if (this.lineMatchesOffer(line, offer)) {
////                if (this.applyDiscount(line, offer)) applied++;
////            }
////        }
////        if (applied > 0) {
////            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
////        } else {
////            this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
////        }
////    }
////
////    async applyCoupon() {
////        this.state.errorMsg   = "";
////        this.state.appliedMsg = "";
////        const code = this.state.couponInput.trim();
////        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
////
////        const allOffers = this.offerService.getActiveOffers();
////        let matchedOffer = null;
////        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
////
////        for (const offer of allOffers) {
////            if (offer.offer_type !== "coupon") continue;
////
////            // 1. Check generated codes first
////            if (offer.generated_codes && offer.generated_codes.length > 0) {
////                const found = offer.generated_codes.find(
////                    c => c.code.toLowerCase() === code.toLowerCase()
////                );
////                if (found) {
////                    matchedOffer  = offer;
////                    matchedCoupon = found;
////                    break;
////                }
////            }
////
////            // 2. Fall back to single coupon_code
////            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
////                matchedOffer = offer;
////                break;
////            }
////        }
////
////        if (!matchedOffer) {
////            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
////            return;
////        }
////
////        // Apply the discount
////        this.applyOffer(matchedOffer);
////
////        // Mark generated coupon as used on the server
////        if (matchedCoupon && this.state.appliedMsg) {
////            try {
////                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
////                // Remove from local offer list so it can't be reused in this session
////                if (matchedCoupon.single_use) {
////                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
////                        c => c.id !== matchedCoupon.id
////                    );
////                }
////            } catch(e) {
////                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
////            }
////        }
////
////        this.state.couponInput = "";
////    }
////
////    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
////}
///** @odoo-module **/
//import { Component, useState } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { usePos } from "@point_of_sale/app/hooks/pos_hook";
//
//export class SpecialOfferPopup extends Component {
//    static template = "pos_special_offers.SpecialOfferPopup";
//    static props = { close: Function };
//
//    setup() {
//        this.pos = usePos();
//        this.offerService = useService("special_offer_service");
//        this.orm = useService("orm");
//        this.state = useState({
//            couponInput: "",
//            appliedMsg:  "",
//            errorMsg:    "",
//            refreshing:  false,
//        });
//    }
//
//    async onRefresh() {
//        this.state.refreshing = true;
//        this.state.appliedMsg = "";
//        this.state.errorMsg   = "";
//        try {
//            await this.offerService.refresh();
//        } catch(e) {
//            this.state.errorMsg = "Refresh failed. Check your connection.";
//        } finally {
//            this.state.refreshing = false;
//        }
//    }
//
//    get allFlatOffers() {
//        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
//    }
//
//    get currentOrder() {
//        const p = this.pos;
//        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
//        catch(e) { return null; }
//    }
//
//    getOrderLines(order) {
//        if (!order) return [];
//        try {
//            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
//            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
//            if (Array.isArray(order.orderlines))            return order.orderlines;
//            if (order.orderlines?.models)                   return order.orderlines.models;
//        } catch(e) {}
//        return [];
//    }
//
//    getProductId(line) {
//        try {
//            if (line.product_id?.id)                    return line.product_id.id;
//            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
//            if (line.product?.id)                       return line.product.id;
//            if (typeof line.product_id === "number")    return line.product_id;
//        } catch(e) {}
//        return null;
//    }
//
//    getProductCategoryIds(line) {
//        try {
//            const product = line.product_id ?? line.product ?? line.get_product?.();
//            if (!product) return [];
//            const cat = product.categ_id ?? product.category_id;
//            if (!cat) return [];
//            const catId = typeof cat === "object" ? cat.id : cat;
//            return catId ? [catId] : [];
//        } catch(e) { return []; }
//    }
//
//    lineMatchesOffer(line, offer) {
//        if (offer.all_products)   return true;
//        if (offer.all_categories) return true;
//        const pid    = this.getProductId(line);
//        const catIds = this.getProductCategoryIds(line);
//        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))            return true;
//        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
//        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
//        return false;
//    }
//
//    /**
//     * FIXED: For 'fixed' discount type, we now SUBTRACT the discount value
//     * from the current unit price instead of replacing it.
//     * For 'percentage', we apply it as a discount % (unchanged).
//     */
//    applyDiscount(line, offer) {
//        try {
//            if (offer.discount_type === "percentage") {
//                // Percentage discount — set the % discount field
//                if (typeof line.set_discount === "function") {
//                    line.set_discount(offer.discount_value);
//                    return true;
//                }
//                if ("discount" in line) {
//                    line.discount = offer.discount_value;
//                    return true;
//                }
//            } else {
//                // Fixed amount discount — SUBTRACT from current price
//                let currentPrice = null;
//
//                // Get current unit price
//                if (typeof line.get_unit_price === "function") {
//                    currentPrice = line.get_unit_price();
//                } else if (typeof line.getUnitPrice === "function") {
//                    currentPrice = line.getUnitPrice();
//                } else if (line.price_unit !== undefined) {
//                    currentPrice = line.price_unit;
//                } else if (line.price !== undefined) {
//                    currentPrice = line.price;
//                }
//
//                if (currentPrice === null || currentPrice === undefined) {
//                    console.warn("[SpecialOffer] Could not get current price for line");
//                    return false;
//                }
//
//                // Calculate new price after deducting fixed amount (minimum 0)
//                const newPrice = Math.max(0, currentPrice - offer.discount_value);
//
//                if (typeof line.set_unit_price === "function") {
//                    line.set_unit_price(newPrice);
//                    return true;
//                }
//                if (typeof line.setUnitPrice === "function") {
//                    line.setUnitPrice(newPrice);
//                    return true;
//                }
//                if ("price_unit" in line) {
//                    line.price_unit = newPrice;
//                    return true;
//                }
//            }
//        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
//        return false;
//    }
//
//    getSelectedLine(order) {
//        try {
//            // Odoo 17/18/19 POS — various ways to get the selected/highlighted line
//            if (typeof order.get_selected_orderline === "function") return order.get_selected_orderline();
//            if (typeof order.getSelectedOrderline  === "function") return order.getSelectedOrderline();
//            if (order.selected_orderline)  return order.selected_orderline;
//            if (order.selectedOrderline)   return order.selectedOrderline;
//        } catch(e) {}
//        return null;
//    }
//
//    /**
//     * For FLAT DISCOUNT offers: apply to all matching lines (existing behaviour).
//     * For COUPON offers: apply only to the currently selected order line.
//     */
//    applyOffer(offer, couponMode = false) {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const order = this.currentOrder;
//        if (!order) { this.state.errorMsg = "No active order found."; return; }
//
//        if (couponMode) {
//            // ── Coupon: apply only to the selected line ───────────────────────
//            const line = this.getSelectedLine(order);
//            if (!line) {
//                this.state.errorMsg = "Please select a product line in the order first.";
//                return;
//            }
//            if (!this.lineMatchesOffer(line, offer)) {
//                const lines = this.getOrderLines(order);
//                if (!lines.length) {
//                    this.state.errorMsg = "Please add products to the order first.";
//                    return;
//                }
//                // Offer doesn't match the selected line — still apply (coupon applies regardless of product scope when used manually)
//            }
//            if (this.applyDiscount(line, offer)) {
//                this.state.appliedMsg = `✅ "${offer.name}" applied to selected product!`;
//            } else {
//                this.state.errorMsg = `Could not apply "${offer.name}" to the selected line.`;
//            }
//        } else {
//            // ── Flat discount: apply to ALL matching lines (unchanged) ────────
//            const lines = this.getOrderLines(order);
//            if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
//            let applied = 0;
//            for (const line of lines) {
//                if (this.lineMatchesOffer(line, offer)) {
//                    if (this.applyDiscount(line, offer)) applied++;
//                }
//            }
//            if (applied > 0) {
//                this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
//            } else {
//                this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
//            }
//        }
//    }
//
//    async applyCoupon() {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const code = this.state.couponInput.trim();
//        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
//
//        const allOffers = this.offerService.getActiveOffers();
//        let matchedOffer = null;
//        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
//
//        for (const offer of allOffers) {
//            if (offer.offer_type !== "coupon") continue;
//
//            // 1. Check generated codes first
//            if (offer.generated_codes && offer.generated_codes.length > 0) {
//                const found = offer.generated_codes.find(
//                    c => c.code.toLowerCase() === code.toLowerCase()
//                );
//                if (found) {
//                    matchedOffer  = offer;
//                    matchedCoupon = found;
//                    break;
//                }
//            }
//
//            // 2. Fall back to single coupon_code
//            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
//                matchedOffer = offer;
//                break;
//            }
//        }
//
//        if (!matchedOffer) {
//            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
//            return;
//        }
//
//        // Apply the discount only to the selected line (coupon mode)
//        this.applyOffer(matchedOffer, true);
//
//        // Mark generated coupon as used on the server
//        if (matchedCoupon && this.state.appliedMsg) {
//            try {
//                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
//                // Remove from local offer list so it can't be reused in this session
//                if (matchedCoupon.single_use) {
//                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
//                        c => c.id !== matchedCoupon.id
//                    );
//                }
//            } catch(e) {
//                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
//            }
//        }
//
//        this.state.couponInput = "";
//    }
//
//    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
//}
///** @odoo-module **/
//import { Component, useState } from "@odoo/owl";
//import { useService } from "@web/core/utils/hooks";
//import { usePos } from "@point_of_sale/app/hooks/pos_hook";
//
//export class SpecialOfferPopup extends Component {
//    static template = "pos_special_offers.SpecialOfferPopup";
//    static props = { close: Function };
//
//    setup() {
//        this.pos = usePos();
//        this.offerService = useService("special_offer_service");
//        this.orm = useService("orm");
//        this.state = useState({
//            couponInput: "",
//            appliedMsg:  "",
//            errorMsg:    "",
//            refreshing:  false,
//        });
//    }
//
//    async onRefresh() {
//        this.state.refreshing = true;
//        this.state.appliedMsg = "";
//        this.state.errorMsg   = "";
//        try {
//            await this.offerService.refresh();
//        } catch(e) {
//            this.state.errorMsg = "Refresh failed. Check your connection.";
//        } finally {
//            this.state.refreshing = false;
//        }
//    }
//
//    get allFlatOffers() {
//        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
//    }
//
//    get currentOrder() {
//        const p = this.pos;
//        try { return p.get_order?.() ?? p.selectedOrder ?? p.currentOrder ?? null; }
//        catch(e) { return null; }
//    }
//
//    getOrderLines(order) {
//        if (!order) return [];
//        try {
//            if (Array.isArray(order.lines) && order.lines.length > 0) return order.lines;
//            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
//            if (Array.isArray(order.orderlines))            return order.orderlines;
//            if (order.orderlines?.models)                   return order.orderlines.models;
//        } catch(e) {}
//        return [];
//    }
//
//    getProductId(line) {
//        try {
//            if (line.product_id?.id)                    return line.product_id.id;
//            if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
//            if (line.product?.id)                       return line.product.id;
//            if (typeof line.product_id === "number")    return line.product_id;
//        } catch(e) {}
//        return null;
//    }
//
//    getProductCategoryIds(line) {
//        try {
//            const product = line.product_id ?? line.product ?? line.get_product?.();
//            if (!product) return [];
//            const cat = product.categ_id ?? product.category_id;
//            if (!cat) return [];
//            const catId = typeof cat === "object" ? cat.id : cat;
//            return catId ? [catId] : [];
//        } catch(e) { return []; }
//    }
//
//    lineMatchesOffer(line, offer) {
//        if (offer.all_products)   return true;
//        if (offer.all_categories) return true;
//        const pid    = this.getProductId(line);
//        const catIds = this.getProductCategoryIds(line);
//        if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))           return true;
//        if (offer.category_ids.length > 0 && catIds.some(c => offer.category_ids.includes(c))) return true;
//        if (offer.product_ids.length === 0 && offer.category_ids.length === 0)                  return true;
//        return false;
//    }
//
//    applyDiscount(line, offer) {
//        try {
//            if (offer.discount_type === "percentage") {
//                if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
//                if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
//            } else {
//                if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
//                if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
//                if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
//            }
//        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
//        return false;
//    }
//
//    applyOffer(offer) {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const order = this.currentOrder;
//        if (!order) { this.state.errorMsg = "No active order found."; return; }
//        const lines = this.getOrderLines(order);
//        if (!lines.length) { this.state.errorMsg = "Please add products to the order first."; return; }
//        let applied = 0;
//        for (const line of lines) {
//            if (this.lineMatchesOffer(line, offer)) {
//                if (this.applyDiscount(line, offer)) applied++;
//            }
//        }
//        if (applied > 0) {
//            this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} line(s)!`;
//        } else {
//            this.state.errorMsg = `"${offer.name}" matched no products in this order.`;
//        }
//    }
//
//    async applyCoupon() {
//        this.state.errorMsg   = "";
//        this.state.appliedMsg = "";
//        const code = this.state.couponInput.trim();
//        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }
//
//        const allOffers = this.offerService.getActiveOffers();
//        let matchedOffer = null;
//        let matchedCoupon = null;  // {id, code, single_use} from generated_codes
//
//        for (const offer of allOffers) {
//            if (offer.offer_type !== "coupon") continue;
//
//            // 1. Check generated codes first
//            if (offer.generated_codes && offer.generated_codes.length > 0) {
//                const found = offer.generated_codes.find(
//                    c => c.code.toLowerCase() === code.toLowerCase()
//                );
//                if (found) {
//                    matchedOffer  = offer;
//                    matchedCoupon = found;
//                    break;
//                }
//            }
//
//            // 2. Fall back to single coupon_code
//            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
//                matchedOffer = offer;
//                break;
//            }
//        }
//
//        if (!matchedOffer) {
//            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
//            return;
//        }
//
//        // Apply the discount
//        this.applyOffer(matchedOffer);
//
//        // Mark generated coupon as used on the server
//        if (matchedCoupon && this.state.appliedMsg) {
//            try {
//                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
//                // Remove from local offer list so it can't be reused in this session
//                if (matchedCoupon.single_use) {
//                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
//                        c => c.id !== matchedCoupon.id
//                    );
//                }
//            } catch(e) {
//                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
//            }
//        }
//
//        this.state.couponInput = "";
//    }
//
//    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
//}
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
        this.orm = useService("orm");
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
        return this.offerService.getActiveOffers().filter(o => o.offer_type === "flat_discount");
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
            if (typeof order.get_orderlines === "function") return order.get_orderlines() || [];
            if (Array.isArray(order.orderlines))            return order.orderlines;
            if (order.orderlines?.models)                   return order.orderlines.models;
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
        const pid    = this.getProductId(line);
        const catIds = this.getProductCategoryIds(line);

        // ── Exclusion check (takes priority over everything) ──────────────────
        if (pid && offer.exclude_product_ids && offer.exclude_product_ids.includes(pid))
            return false;
        if (catIds.length && offer.exclude_category_ids && offer.exclude_category_ids.length)
            if (catIds.some(c => offer.exclude_category_ids.includes(c))) return false;

        // ── Inclusion check ───────────────────────────────────────────────────
        if (offer.all_products)   return true;
        if (offer.all_categories) return true;
        // Check specific product list
        if (offer.product_ids && offer.product_ids.length > 0) {
            if (pid && offer.product_ids.includes(pid)) return true;
        }
        // Check specific category list
        if (offer.category_ids && offer.category_ids.length > 0) {
            if (catIds.some(c => offer.category_ids.includes(c))) return true;
        }
        // FIX: Do NOT fall back to "match all" when both lists are empty.
        // An offer with no all_products/all_categories and no specific products/categories
        // should NOT match anything — prevents applying to unintended products.
        return false;
    }

    /**
     * FIXED: For 'fixed' discount type, we now SUBTRACT the discount value
     * from the current unit price instead of replacing it.
     * For 'percentage', we apply it as a discount % (unchanged).
     */
    applyDiscount(line, offer) {
        try {
            if (offer.discount_type === "percentage") {
                // Percentage discount — set the % discount field
                if (typeof line.set_discount === "function") {
                    line.set_discount(offer.discount_value);
                    return true;
                }
                if ("discount" in line) {
                    line.discount = offer.discount_value;
                    return true;
                }
            } else {
                // Fixed amount discount — SUBTRACT from current price
                let currentPrice = null;

                // Get current unit price
                if (typeof line.get_unit_price === "function") {
                    currentPrice = line.get_unit_price();
                } else if (typeof line.getUnitPrice === "function") {
                    currentPrice = line.getUnitPrice();
                } else if (line.price_unit !== undefined) {
                    currentPrice = line.price_unit;
                } else if (line.price !== undefined) {
                    currentPrice = line.price;
                }

                if (currentPrice === null || currentPrice === undefined) {
                    console.warn("[SpecialOffer] Could not get current price for line");
                    return false;
                }

                // Calculate new price after deducting fixed amount (minimum 0)
                const newPrice = Math.max(0, currentPrice - offer.discount_value);

                if (typeof line.set_unit_price === "function") {
                    line.set_unit_price(newPrice);
                    return true;
                }
                if (typeof line.setUnitPrice === "function") {
                    line.setUnitPrice(newPrice);
                    return true;
                }
                if ("price_unit" in line) {
                    line.price_unit = newPrice;
                    return true;
                }
            }
        } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
        return false;
    }

    getSelectedLine(order) {
        try {
            // Odoo 17/18/19 POS — various ways to get the selected/highlighted line
            if (typeof order.get_selected_orderline === "function") return order.get_selected_orderline();
            if (typeof order.getSelectedOrderline  === "function") return order.getSelectedOrderline();
            if (order.selected_orderline)  return order.selected_orderline;
            if (order.selectedOrderline)   return order.selectedOrderline;
        } catch(e) {}
        return null;
    }

    /**
     * For FLAT DISCOUNT offers: apply to all matching lines (existing behaviour).
     * For COUPON offers: apply only to the currently selected order line.
     */
    applyOffer(offer, couponMode = false) {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";
        const order = this.currentOrder;
        if (!order) { this.state.errorMsg = "No active order found."; return; }

        if (couponMode) {
            // ── Coupon: apply to ALL matching lines in the order ──────────────
            // Enforces product/category scope — only lines matching the offer are discounted.
            const lines = this.getOrderLines(order);
            if (!lines.length) {
                this.state.errorMsg = "Please add products to the order first.";
                return;
            }
            let applied = 0;
            for (const line of lines) {
                if (this.lineMatchesOffer(line, offer)) {
                    if (this.applyDiscount(line, offer)) applied++;
                }
            }
            if (applied > 0) {
                this.state.appliedMsg = `✅ "${offer.name}" applied to ${applied} matching product(s)!`;
            } else {
                this.state.errorMsg = `This coupon is only valid for specific products not present in this order.`;
            }
        } else {
            // ── Flat discount: apply to ALL matching lines (unchanged) ────────
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
    }

    async applyCoupon() {
        this.state.errorMsg   = "";
        this.state.appliedMsg = "";
        const code = this.state.couponInput.trim();
        if (!code) { this.state.errorMsg = "Please enter a coupon code."; return; }

        const allOffers = this.offerService.getActiveOffers();
        let matchedOffer = null;
        let matchedCoupon = null;  // {id, code, single_use} from generated_codes

        for (const offer of allOffers) {
            if (offer.offer_type !== "coupon") continue;

            // 1. Check generated codes first
            if (offer.generated_codes && offer.generated_codes.length > 0) {
                const found = offer.generated_codes.find(
                    c => c.code.toLowerCase() === code.toLowerCase()
                );
                if (found) {
                    matchedOffer  = offer;
                    matchedCoupon = found;
                    break;
                }
            }

            // 2. Fall back to single coupon_code
            if (offer.coupon_code && offer.coupon_code.toLowerCase() === code.toLowerCase()) {
                matchedOffer = offer;
                break;
            }
        }

        if (!matchedOffer) {
            this.state.errorMsg = `Coupon "${code}" is invalid or expired.`;
            return;
        }

        // Apply the discount only to the selected line (coupon mode)
        this.applyOffer(matchedOffer, true);

        // Mark generated coupon as used on the server
        if (matchedCoupon && this.state.appliedMsg) {
            try {
                await this.orm.call("pos.special.offer", "mark_coupon_used", [matchedCoupon.id]);
                // Remove from local offer list so it can't be reused in this session
                if (matchedCoupon.single_use) {
                    matchedOffer.generated_codes = matchedOffer.generated_codes.filter(
                        c => c.id !== matchedCoupon.id
                    );
                }
            } catch(e) {
                console.warn("[SpecialOffer] mark_coupon_used failed:", e);
            }
        }

        this.state.couponInput = "";
    }

    onCouponInput(ev) { this.state.couponInput = ev.target.value; }
}