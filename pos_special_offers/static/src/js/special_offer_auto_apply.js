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

// ── Patch PosOrderline setup() ───────────────────────────────────────────────
// In Odoo 19, each orderline is a reactive model object.
// We patch the PosOrderline class - when a new line is created (setup called),
// we auto-apply the offer after a short delay to let the line fully initialize.
function patchPosOrderline() {
    const mod = odoo.loader.modules.get("@point_of_sale/app/models/pos_order_line");
    if (!mod?.PosOrderline) {
        console.warn("[SpecialOffer] PosOrderline not found, trying alternate path...");
        return false;
    }

    const proto = mod.PosOrderline.prototype;
    console.log("[SpecialOffer] PosOrderline methods:", Object.getOwnPropertyNames(proto).join(", "));

    // Patch 'setup' - called when a new line is instantiated in Odoo 19 ORM
    if (typeof proto.setup === "function") {
        const originalSetup = proto.setup;
        proto.setup = function(...args) {
            originalSetup.apply(this, args);
            // Wait for product_id to be set on the reactive object
            setTimeout(() => {
                try {
                    const pid = getLineProductId(this);
                    if (pid) {
                        console.log("[SpecialOffer] New line setup, product:", pid);
                        autoApplyToLine(this);
                    }
                } catch(e) {
                    console.warn("[SpecialOffer] setup hook error:", e);
                }
            }, 100);
        };
        console.log("[SpecialOffer] ✅ Patched PosOrderline.setup");
        return true;
    }

    return false;
}

// ── Fallback: patch PosOrder.select_orderline or use MutationObserver ────────
function patchViaOrderlineCreation() {
    // Scan ALL pos modules for PosOrderline
    for (const [path, mod] of odoo.loader.modules) {
        if (!path.includes("point_of_sale")) continue;
        if (!mod?.PosOrderline) continue;

        const proto = mod.PosOrderline.prototype;
        const methods = Object.getOwnPropertyNames(proto);
        console.log(`[SpecialOffer] Found PosOrderline at ${path}, methods:`, methods.join(", "));

        // Try patching 'setup'
        if (typeof proto.setup === "function") {
            const orig = proto.setup;
            proto.setup = function(...args) {
                orig.apply(this, args);
                setTimeout(() => {
                    try {
                        if (getLineProductId(this)) autoApplyToLine(this);
                    } catch(e) {}
                }, 100);
            };
            console.log(`[SpecialOffer] ✅ Patched PosOrderline.setup at ${path}`);
            return true;
        }

        // Try patching 'initialize'
        if (typeof proto.initialize === "function") {
            const orig = proto.initialize;
            proto.initialize = function(...args) {
                orig.apply(this, args);
                setTimeout(() => {
                    try {
                        if (getLineProductId(this)) autoApplyToLine(this);
                    } catch(e) {}
                }, 100);
            };
            console.log(`[SpecialOffer] ✅ Patched PosOrderline.initialize at ${path}`);
            return true;
        }
    }
    return false;
}

// ── Run patches ──────────────────────────────────────────────────────────────
if (!patchPosOrderline()) {
    if (!patchViaOrderlineCreation()) {
        console.warn("[SpecialOffer] ⚠️ Could not patch PosOrderline. Logging all POS modules:");
        for (const [path, mod] of odoo.loader.modules) {
            if (path.includes("point_of_sale") && path.includes("order")) {
                console.log(`  ${path}:`, Object.keys(mod || {}));
            }
        }
    }
}
