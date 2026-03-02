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

// ── Pending queue: lines waiting to be processed after render ────────────────
const pendingLines = new WeakSet();

function scheduleAutoApply(line) {
    // Guard: don't queue the same line twice
    if (pendingLines.has(line)) return;
    pendingLines.add(line);

    // Use setTimeout(200) to ensure OWL has fully rendered the line
    // before we mutate any reactive state
    setTimeout(() => {
        try {
            const pid = getLineProductId(line);
            if (!pid) return; // Skip tip lines, gift cards etc.

            const service = getOfferService();
            if (!service) return;

            const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
            for (const offer of offers) {
                if (lineMatchesOffer(line, offer)) {
                    if (applyDiscountToLine(line, offer)) {
                        console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" to product:`, pid);
                        break;
                    }
                }
            }
        } catch(e) {
            console.warn("[SpecialOffer] scheduleAutoApply error:", e);
        }
    }, 200);
}

// ── Patch PosOrderline.setOptions ────────────────────────────────────────────
// setOptions is called when a line is created with a product.
// We ONLY schedule (never apply synchronously) to avoid OWL render conflicts.
function patchPosOrderline() {
    const mod = odoo.loader.modules.get("@point_of_sale/app/models/pos_order_line");
    if (!mod?.PosOrderline) {
        console.warn("[SpecialOffer] PosOrderline not found");
        return false;
    }

    const proto = mod.PosOrderline.prototype;

    // Track which lines were loaded from saved order (not newly added)
    // setOptions is called with options.extras or similar for loaded lines
    const methodsToTry = ["setOptions", "initState", "setup"];

    for (const method of methodsToTry) {
        if (typeof proto[method] !== "function") continue;

        const orig = proto[method];
        proto[method] = function(...args) {
            // Call original FIRST - let OWL set up the line completely
            orig.apply(this, args);
            // Schedule discount application AFTER render completes
            scheduleAutoApply(this);
        };
        console.log(`[SpecialOffer] ✅ Patched PosOrderline.${method} (deferred apply)`);
        // Only patch the first found method
        break;
    }

    return true;
}

patchPosOrderline();
