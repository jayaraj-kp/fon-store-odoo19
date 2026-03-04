/** @odoo-module **/
/**
 * POS Special Offers — Auto Apply
 *
 * Confirmed Odoo 19 internals (from live console diagnostics):
 *   PosStore path   : @point_of_sale/app/services/pos_store
 *   Hook method     : addLineToCurrentOrder(product, options)
 *                     → returns the newly created PosOrderline
 *
 * We patch addLineToCurrentOrder so the discount fires immediately
 * after the line is created — completely outside OWL's render cycle,
 * and never triggered during session restore.
 */

// ── Helpers ──────────────────────────────────────────────────────────────────

function getOfferService() {
    try {
        for (const app of (owl.__apps__ || [])) {
            const svc = app?.env?.services?.special_offer_service;
            if (svc) return svc;
        }
    } catch(e) {}
    return null;
}

function getProductId(line) {
    try {
        if (line.product_id?.id)                    return line.product_id.id;
        if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
        if (line.product?.id)                       return line.product.id;
        if (typeof line.product_id === "number")    return line.product_id;
    } catch(e) {}
    return null;
}

function getCategoryId(line) {
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
    const pid   = getProductId(line);
    const catId = getCategoryId(line);
    if (offer.product_ids.length  > 0 && pid   && offer.product_ids.includes(pid))   return true;
    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId)) return true;
    // No filter at all → apply to every product
    if (offer.product_ids.length === 0 && offer.category_ids.length === 0)            return true;
    return false;
}

function applyDiscount(line, offer) {
    try {
        if (offer.discount_type === "percentage") {
            if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
            if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
        } else {
            // fixed price
            if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
            if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
            if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
        }
    } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
    return false;
}

function autoApply(line) {
    if (!line) return;
    const pid = getProductId(line);
    if (!pid) return;  // skip tip / reward / gift-card lines

    const service = getOfferService();
    if (!service) return;

    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    for (const offer of offers) {
        if (lineMatchesOffer(line, offer)) {
            if (applyDiscount(line, offer)) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" → product ${pid}`);
                break;  // first matching offer wins
            }
        }
    }
}

// ── Patch PosStore ────────────────────────────────────────────────────────────
(function patch() {
    // Confirmed path from live Odoo 19 console
    const mod = odoo.loader.modules.get("@point_of_sale/app/services/pos_store");

    if (!mod?.PosStore) {
        console.warn("[SpecialOffer] PosStore not found — auto-apply disabled.");
        return;
    }

    const proto = mod.PosStore.prototype;

    // ── Primary: addLineToCurrentOrder ───────────────────────────────────────
    // Confirmed present in Odoo 19, returns the new orderline directly.
    if (typeof proto.addLineToCurrentOrder === "function") {
        const _orig = proto.addLineToCurrentOrder;
        proto.addLineToCurrentOrder = async function(product, options = {}) {
            const line = await _orig.call(this, product, options);
            try { autoApply(line); } catch(e) { /* never crash POS */ }
            return line;
        };
        console.log("[SpecialOffer] ✅ Auto-apply ready (hooked addLineToCurrentOrder)");
        return;
    }

    // ── Fallback: addLineToOrder ──────────────────────────────────────────────
    if (typeof proto.addLineToOrder === "function") {
        const _orig = proto.addLineToOrder;
        proto.addLineToOrder = async function(product, options = {}, order) {
            const line = await _orig.call(this, product, options, order);
            try { autoApply(line); } catch(e) { /* never crash POS */ }
            return line;
        };
        console.log("[SpecialOffer] ✅ Auto-apply ready (hooked addLineToOrder)");
        return;
    }

    console.warn("[SpecialOffer] ⚠️ No suitable hook found on PosStore — auto-apply disabled.");
})();
