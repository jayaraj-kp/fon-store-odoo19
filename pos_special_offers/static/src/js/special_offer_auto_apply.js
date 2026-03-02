/** @odoo-module **/
import { patch } from "@web/core/utils/patch";

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

function autoApplyToLine(line) {
    const service = getOfferService();
    if (!service) { console.warn("[SpecialOffer] No service found"); return; }
    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    console.log("[SpecialOffer] autoApplyToLine - offers:", offers.length, "line product:", getLineProductId(line));
    for (const offer of offers) {
        if (lineMatchesOffer(line, offer)) {
            if (applyDiscountToLine(line, offer)) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}"`);
                break;
            }
        }
    }
}

// ── Find the last added line after product addition ──────────────────────────
function getLastLine(order) {
    // Odoo 19: order.lines is a direct reactive array
    if (Array.isArray(order.lines) && order.lines.length > 0)
        return order.lines[order.lines.length - 1];
    // Odoo 17/18: get_orderlines()
    if (typeof order.get_orderlines === "function") {
        const lines = order.get_orderlines();
        return lines?.[lines.length - 1] ?? null;
    }
    if (order.orderlines?.models?.length)
        return order.orderlines.models[order.orderlines.models.length - 1];
    return null;
}

// ── Patch PosOrder ───────────────────────────────────────────────────────────
function patchPosOrder() {
    const mod = odoo.loader.modules.get("@point_of_sale/app/models/pos_order");
    if (!mod?.PosOrder) {
        console.warn("[SpecialOffer] PosOrder module not found");
        return false;
    }

    const PosOrder = mod.PosOrder;

    // Log all method names to find the correct add product method
    const proto = PosOrder.prototype;
    const methods = Object.getOwnPropertyNames(proto).filter(m =>
        m.toLowerCase().includes("add") || m.toLowerCase().includes("product")
    );
    console.log("[SpecialOffer] PosOrder methods with 'add/product':", methods);

    // Patch every possible method name Odoo 19 might use
    const methodNames = ["add_product", "addProduct", "addOrderline", "add_orderline"];

    for (const methodName of methodNames) {
        if (typeof proto[methodName] === "function") {
            const original = proto[methodName];
            proto[methodName] = function(...args) {
                const result = original.apply(this, args);
                // Use setTimeout to wait for the line to be fully added
                setTimeout(() => {
                    try {
                        const line = getLastLine(this);
                        if (line) {
                            console.log("[SpecialOffer] Hooked via:", methodName, "line:", line);
                            autoApplyToLine(line);
                        }
                    } catch(e) {
                        console.warn("[SpecialOffer] Hook error:", e);
                    }
                }, 50);
                return result;
            };
            console.log(`[SpecialOffer] ✅ Patched PosOrder.${methodName}`);
        }
    }

    return true;
}

patchPosOrder();
