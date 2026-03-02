/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

function getOfferService(env) {
    try {
        return env?.services?.special_offer_service ?? null;
    } catch(e) { return null; }
}

function getLineProductId(line) {
    try {
        if (line.product_id?.id)                    return line.product_id.id;
        if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
        if (line.product?.id)                       return line.product.id;
        if (typeof line.product_id === "number")    return line.product_id;
    } catch(e) {}
    return null;
}

function getLineCategoryId(line) {
    try {
        const product = line.product_id ?? line.product ?? line.get_product?.();
        if (!product) return null;
        const cat = product.categ_id ?? product.category_id;
        if (!cat) return null;
        return typeof cat === "object" ? cat.id : cat;
    } catch(e) { return null; }
}

function lineMatchesOffer(line, offer) {
    if (offer.all_products)   return true;
    if (offer.all_categories) return true;
    const pid   = getLineProductId(line);
    const catId = getLineCategoryId(line);
    if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))       return true;
    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId)) return true;
    if (offer.product_ids.length === 0 && offer.category_ids.length === 0)             return true;
    return false;
}

function applyDiscountToLine(line, offer) {
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

// ── Patch PosStore.addProductToCurrentOrder ──────────────────────────────────
// PosStore is the high-level store. It has addProductToCurrentOrder which is
// called when the cashier clicks a product tile. This runs OUTSIDE OWL render.
patch(PosStore.prototype, {
    async addProductToCurrentOrder(product, options = {}) {
        // Call original method first
        await super.addProductToCurrentOrder(product, options);

        // Now safely apply offer — we are outside the render cycle here
        try {
            const service = getOfferService(this.env);
            if (!service) return;

            const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
            if (!offers.length) return;

            // Get the current order and its last line
            const order = this.get_order?.() ?? this.selectedOrder ?? this.currentOrder;
            if (!order) return;

            const lines = Array.isArray(order.lines) ? order.lines :
                          order.get_orderlines?.() ||
                          order.orderlines?.models || [];
            if (!lines.length) return;

            const lastLine = lines[lines.length - 1];
            if (!lastLine) return;

            const pid = getLineProductId(lastLine);
            if (!pid) return;

            for (const offer of offers) {
                if (lineMatchesOffer(lastLine, offer)) {
                    if (applyDiscountToLine(lastLine, offer)) {
                        console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" to product:`, pid);
                        break;
                    }
                }
            }
        } catch(e) {
            console.warn("[SpecialOffer] addProductToCurrentOrder hook error:", e);
        }
    }
});

console.log("[SpecialOffer] ✅ Patched PosStore.addProductToCurrentOrder");
