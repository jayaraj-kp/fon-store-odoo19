///** @odoo-module **/
//
//// ── Service locator: finds special_offer_service from the POS OWL env ────────
//// The issue: owl.__apps__ doesn't expose services in Odoo 19 POS.
//// Solution: store a reference to the service at registration time.
//
//let _cachedService = null;
//
//// Called by special_offer_service.js after it starts (see below)
//export function registerAutoApplyService(service) {
//    _cachedService = service;
//    console.log("[SpecialOffer] ✅ Service registered for auto-apply");
//}
//
//function getOfferService() {
//    return _cachedService;
//}
//
//function getProductId(line) {
//    try {
//        if (line.product_id?.id)                    return line.product_id.id;
//        if (typeof line.get_product === "function") return line.get_product()?.id ?? null;
//        if (line.product?.id)                       return line.product.id;
//        if (typeof line.product_id === "number")    return line.product_id;
//    } catch(e) {}
//    return null;
//}
//
//function getCategoryId(line) {
//    try {
//        const product = line.product_id ?? line.product ?? line.get_product?.();
//        if (!product) return null;
//        const cat = product.categ_id ?? product.category_id;
//        if (!cat) return null;
//        return typeof cat === "object" ? cat.id : cat;
//    } catch(e) { return null; }
//}
//
//function lineMatchesOffer(line, offer) {
//    if (offer.all_products)   return true;
//    if (offer.all_categories) return true;
//    const pid   = getProductId(line);
//    const catId = getCategoryId(line);
//    if (offer.product_ids.length  > 0 && pid   && offer.product_ids.includes(pid))    return true;
//    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId)) return true;
//    if (offer.product_ids.length === 0 && offer.category_ids.length === 0)             return true;
//    return false;
//}
//
//function applyDiscount(line, offer) {
//    try {
//        if (offer.discount_type === "percentage") {
//            if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
//            if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
//        } else {
//            if (typeof line.set_unit_price === "function") { line.set_unit_price(offer.discount_value); return true; }
//            if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(offer.discount_value);   return true; }
//            if ("price_unit" in line)                      { line.price_unit = offer.discount_value;    return true; }
//        }
//    } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
//    return false;
//}
//
//function autoApply(line) {
//    if (!line) return;
//    const pid = getProductId(line);
//    if (!pid) return;
//
//    const service = getOfferService();
//    if (!service) {
//        console.warn("[SpecialOffer] autoApply: service not ready yet");
//        return;
//    }
//
//    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
//    for (const offer of offers) {
//        if (lineMatchesOffer(line, offer)) {
//            if (applyDiscount(line, offer)) {
//                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" → product ${pid}`);
//                break;
//            }
//        }
//    }
//}
//
//// ── Patch PosStore.addLineToCurrentOrder ─────────────────────────────────────
//(function patch() {
//    const mod = odoo.loader.modules.get("@point_of_sale/app/services/pos_store");
//    if (!mod?.PosStore) {
//        console.warn("[SpecialOffer] PosStore not found — auto-apply disabled");
//        return;
//    }
//    const proto = mod.PosStore.prototype;
//    if (typeof proto.addLineToCurrentOrder === "function") {
//        const _orig = proto.addLineToCurrentOrder;
//        proto.addLineToCurrentOrder = async function(product, options = {}) {
//            const line = await _orig.call(this, product, options);
//            try { autoApply(line); } catch(e) { /* never crash POS */ }
//            return line;
//        };
//        console.log("[SpecialOffer] ✅ Patched addLineToCurrentOrder");
//    }
//})();
/** @odoo-module **/

// ── Service locator: finds special_offer_service from the POS OWL env ────────
let _cachedService = null;

export function registerAutoApplyService(service) {
    _cachedService = service;
    console.log("[SpecialOffer] ✅ Service registered for auto-apply");
}

function getOfferService() {
    return _cachedService;
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
    if (offer.product_ids.length  > 0 && pid   && offer.product_ids.includes(pid))    return true;
    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId)) return true;
    if (offer.product_ids.length === 0 && offer.category_ids.length === 0)             return true;
    return false;
}

/**
 * FIXED: For 'fixed' discount type, SUBTRACT the discount value from the
 * current unit price instead of replacing it with the discount value.
 */
function applyDiscount(line, offer) {
    try {
        if (offer.discount_type === "percentage") {
            // Percentage: set discount % field
            if (typeof line.set_discount === "function") { line.set_discount(offer.discount_value); return true; }
            if ("discount" in line)                      { line.discount = offer.discount_value;    return true; }
        } else {
            // Fixed amount: READ current price then SUBTRACT
            let currentPrice = null;

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
                console.warn("[SpecialOffer] Could not read current price for auto-apply");
                return false;
            }

            const newPrice = Math.max(0, currentPrice - offer.discount_value);

            if (typeof line.set_unit_price === "function") { line.set_unit_price(newPrice); return true; }
            if (typeof line.setUnitPrice   === "function") { line.setUnitPrice(newPrice);   return true; }
            if ("price_unit" in line)                      { line.price_unit = newPrice;     return true; }
        }
    } catch(e) { console.error("[SpecialOffer] applyDiscount error:", e); }
    return false;
}

function autoApply(line) {
    if (!line) return;
    const pid = getProductId(line);
    if (!pid) return;

    const service = getOfferService();
    if (!service) {
        console.warn("[SpecialOffer] autoApply: service not ready yet");
        return;
    }

    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    for (const offer of offers) {
        if (lineMatchesOffer(line, offer)) {
            if (applyDiscount(line, offer)) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" → product ${pid}`);
                break;
            }
        }
    }
}

// ── Patch PosStore.addLineToCurrentOrder ─────────────────────────────────────
(function patch() {
    const mod = odoo.loader.modules.get("@point_of_sale/app/services/pos_store");
    if (!mod?.PosStore) {
        console.warn("[SpecialOffer] PosStore not found — auto-apply disabled");
        return;
    }
    const proto = mod.PosStore.prototype;
    if (typeof proto.addLineToCurrentOrder === "function") {
        const _orig = proto.addLineToCurrentOrder;
        proto.addLineToCurrentOrder = async function(product, options = {}) {
            const line = await _orig.call(this, product, options);
            try { autoApply(line); } catch(e) { /* never crash POS */ }
            return line;
        };
        console.log("[SpecialOffer] ✅ Patched addLineToCurrentOrder");
    }
})();
