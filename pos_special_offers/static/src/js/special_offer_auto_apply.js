/** @odoo-module **/

function getOfferService() {
    try {
        for (const app of (owl.__apps__ || [])) {
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

function doAutoApply(lastLine) {
    if (!lastLine) return;
    const pid = getLineProductId(lastLine);
    if (!pid) return;
    const service = getOfferService();
    if (!service) return;
    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    for (const offer of offers) {
        if (lineMatchesOffer(lastLine, offer)) {
            if (applyDiscountToLine(lastLine, offer)) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" to product:`, pid);
                break;
            }
        }
    }
}

// ── Find PosStore by scanning ALL loaded modules ─────────────────────────────
function findPosStore() {
    const candidates = [];
    for (const [path, mod] of odoo.loader.modules) {
        if (!path.includes("point_of_sale")) continue;
        if (!mod?.PosStore) continue;
        candidates.push(path);
    }
    console.log("[SpecialOffer] PosStore found at:", candidates);
    return candidates.length ? odoo.loader.modules.get(candidates[0])?.PosStore : null;
}

function getLastLine(order) {
    if (!order) return null;
    if (Array.isArray(order.lines) && order.lines.length > 0)
        return order.lines[order.lines.length - 1];
    if (typeof order.get_orderlines === "function") {
        const lines = order.get_orderlines();
        return lines?.[lines.length - 1] ?? null;
    }
    if (order.orderlines?.models?.length)
        return order.orderlines.models[order.orderlines.models.length - 1];
    return null;
}

function patchPosStore() {
    const PosStore = findPosStore();
    if (!PosStore) {
        // Log all POS module paths to find the right one
        console.warn("[SpecialOffer] PosStore not found. All POS modules:");
        for (const [path] of odoo.loader.modules) {
            if (path.includes("point_of_sale")) {
                console.log("  →", path);
            }
        }
        return false;
    }

    const proto = PosStore.prototype;
    const addMethods = Object.getOwnPropertyNames(proto).filter(m =>
        m.toLowerCase().includes("add") || m.toLowerCase().includes("product")
    );
    console.log("[SpecialOffer] PosStore add/product methods:", addMethods);

    // Try addProductToCurrentOrder first, then any other add method
    const methodName = addMethods.find(m =>
        ["addProductToCurrentOrder", "add_product_to_current_order",
         "addProduct", "add_product"].includes(m)
    );

    if (!methodName) {
        console.warn("[SpecialOffer] No suitable method found on PosStore. Methods:", addMethods);
        return false;
    }

    const orig = proto[methodName];
    proto[methodName] = async function(...args) {
        const result = await orig.apply(this, args);
        try {
            const order = this.get_order?.() ?? this.selectedOrder ?? this.currentOrder;
            doAutoApply(getLastLine(order));
        } catch(e) {
            console.warn("[SpecialOffer] auto-apply hook error:", e);
        }
        return result;
    };
    console.log(`[SpecialOffer] ✅ Patched PosStore.${methodName}`);
    return true;
}

patchPosStore();
