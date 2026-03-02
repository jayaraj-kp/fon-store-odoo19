/** @odoo-module **/

// ── NO imports — avoid any dependency issues ─────────────────────────────────
// We use odoo.loader.modules directly to get PosStore at runtime

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
    if (!pid) return; // skip tip/reward/gift lines that have no product

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

// ── Patch PosStore via odoo.loader (no import needed) ────────────────────────
function patchPosStore() {
    const storeMod = odoo.loader.modules.get("@point_of_sale/app/store/pos_store");
    if (!storeMod?.PosStore) {
        console.warn("[SpecialOffer] PosStore not found");
        return false;
    }

    const proto = storeMod.PosStore.prototype;

    // addProductToCurrentOrder is called when cashier clicks a product tile
    if (typeof proto.addProductToCurrentOrder === "function") {
        const orig = proto.addProductToCurrentOrder;
        proto.addProductToCurrentOrder = async function(product, options = {}) {
            const result = await orig.call(this, product, options);
            try {
                const order = this.get_order?.() ?? this.selectedOrder ?? this.currentOrder;
                if (!order) return result;
                const lines = Array.isArray(order.lines) ? order.lines :
                              order.get_orderlines?.() ?? order.orderlines?.models ?? [];
                doAutoApply(lines[lines.length - 1]);
            } catch(e) {
                console.warn("[SpecialOffer] hook error:", e);
            }
            return result;
        };
        console.log("[SpecialOffer] ✅ Patched PosStore.addProductToCurrentOrder");
        return true;
    }

    // Log available methods to help debug if not found
    const methods = Object.getOwnPropertyNames(proto).filter(m =>
        m.toLowerCase().includes("add") || m.toLowerCase().includes("product")
    );
    console.warn("[SpecialOffer] addProductToCurrentOrder not found. Available:", methods);
    return false;
}

// Run after all modules are loaded
patchPosStore();
