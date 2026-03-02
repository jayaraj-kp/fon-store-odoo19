/** @odoo-module **/

function getOfferService() {
    try {
        for (const app of owl.__apps__ || []) {
            const svc = app?.env?.services?.special_offer_service;
            if (svc) return svc;
        }
    } catch(e) {}
    return null;
}

function getLineProductId(line) {
    try {
        if (line.product_id?.id)                        return line.product_id.id;
        if (typeof line.get_product === "function")     return line.get_product()?.id ?? null;
        if (line.product?.id)                           return line.product.id;
        if (typeof line.product_id === "number")        return line.product_id;
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
    if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))        return true;
    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId))  return true;
    if (offer.product_ids.length === 0 && offer.category_ids.length === 0)              return true;
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

function autoApplyToLine(line) {
    const service = getOfferService();
    if (!service) return;
    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    for (const offer of offers) {
        if (lineMatchesOffer(line, offer)) {
            if (applyDiscountToLine(line, offer)) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" to product:`, getLineProductId(line));
                break;
            }
        }
    }
}

function patchPosOrderline() {
    const mod = odoo.loader.modules.get("@point_of_sale/app/models/pos_order_line");
    if (!mod?.PosOrderline) {
        console.warn("[SpecialOffer] PosOrderline not found");
        return false;
    }

    const proto = mod.PosOrderline.prototype;

    // ── Patch setOptions ────────────────────────────────────────────────────
    // setOptions is called AFTER the line is fully initialized with a product.
    // It's the safest hook — product_id is guaranteed to be set at this point.
    if (typeof proto.setOptions === "function") {
        const orig = proto.setOptions;
        proto.setOptions = function(options) {
            orig.call(this, options);
            // Only auto-apply for NEW lines (not restoring from order data)
            // Check options to distinguish new addition vs restore
            if (options && options.new === false) return;
            try {
                const pid = getLineProductId(this);
                if (pid) {
                    console.log("[SpecialOffer] setOptions hook - product:", pid);
                    autoApplyToLine(this);
                }
            } catch(e) {
                console.warn("[SpecialOffer] setOptions hook error:", e);
            }
        };
        console.log("[SpecialOffer] ✅ Patched PosOrderline.setOptions");
        return true;
    }

    // ── Fallback: patch initState ───────────────────────────────────────────
    if (typeof proto.initState === "function") {
        const orig = proto.initState;
        proto.initState = function(...args) {
            orig.apply(this, args);
            try {
                const pid = getLineProductId(this);
                if (pid) {
                    console.log("[SpecialOffer] initState hook - product:", pid);
                    autoApplyToLine(this);
                }
            } catch(e) {
                console.warn("[SpecialOffer] initState hook error:", e);
            }
        };
        console.log("[SpecialOffer] ✅ Patched PosOrderline.initState");
        return true;
    }

    console.warn("[SpecialOffer] Neither setOptions nor initState found on PosOrderline");
    return false;
}

patchPosOrderline();
