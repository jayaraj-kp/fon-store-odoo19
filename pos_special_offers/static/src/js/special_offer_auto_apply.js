/** @odoo-module **/
/**
 * Auto-apply special offers when a product is added to the POS order.
 * We patch PosOrder.add_product / addProduct to trigger offer matching
 * immediately after each line is added.
 */
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

// ── Helper: find the special_offer_service from the OWL app env ──────────────
function getOfferService() {
    try {
        for (const app of owl.__apps__ || []) {
            const svc = app?.env?.services?.special_offer_service;
            if (svc) return svc;
        }
    } catch(e) {}
    return null;
}

// ── Helper: get product id from an order line ────────────────────────────────
function getLineProductId(line) {
    try {
        if (line.product_id?.id)                        return line.product_id.id;
        if (typeof line.get_product === "function")     return line.get_product()?.id ?? null;
        if (line.product?.id)                           return line.product.id;
        if (typeof line.product_id === "number")        return line.product_id;
    } catch(e) {}
    return null;
}

// ── Helper: get product category id from a line ──────────────────────────────
function getLineCategoryId(line) {
    try {
        const product = line.product_id ?? line.product ?? line.get_product?.();
        if (!product) return null;
        const cat = product.categ_id ?? product.category_id;
        if (!cat) return null;
        return typeof cat === "object" ? cat.id : cat;
    } catch(e) { return null; }
}

// ── Helper: check if line matches offer ─────────────────────────────────────
function lineMatchesOffer(line, offer) {
    if (offer.all_products)   return true;
    if (offer.all_categories) return true;

    const pid   = getLineProductId(line);
    const catId = getLineCategoryId(line);

    if (offer.product_ids.length > 0 && pid && offer.product_ids.includes(pid))    return true;
    if (offer.category_ids.length > 0 && catId && offer.category_ids.includes(catId)) return true;

    // nothing selected = applies to all
    if (offer.product_ids.length === 0 && offer.category_ids.length === 0) return true;

    return false;
}

// ── Helper: apply discount to a line ────────────────────────────────────────
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
    } catch(e) { console.error("[SpecialOffer] autoApply discount error:", e); }
    return false;
}

// ── Main auto-apply function ─────────────────────────────────────────────────
function autoApplyOffersToLine(line) {
    const service = getOfferService();
    if (!service) return;

    const offers = service.getActiveOffers().filter(o => o.offer_type === "flat_discount");
    if (!offers.length) return;

    for (const offer of offers) {
        if (lineMatchesOffer(line, offer)) {
            const applied = applyDiscountToLine(line, offer);
            if (applied) {
                console.log(`[SpecialOffer] ✅ Auto-applied "${offer.name}" to line`);
                break; // Apply only the FIRST matching offer per line
            }
        }
    }
}

// ── Patch PosOrder to hook into product addition ─────────────────────────────
const POSORDER_PATHS = [
    "@point_of_sale/app/models/pos_order",
    "@point_of_sale/app/store/pos_order",
];

function tryPatchPosOrder() {
    for (const path of POSORDER_PATHS) {
        try {
            const mod = odoo.loader.modules.get(path);
            if (!mod?.PosOrder) continue;

            patch(mod.PosOrder.prototype, {
                // Odoo 17/18 method name
                add_product(product, options) {
                    const result = super.add_product(product, options);
                    try {
                        // Get the last added line
                        const lines = this.get_orderlines?.() ||
                                      this.orderlines?.models ||
                                      (Array.isArray(this.lines) ? this.lines : []);
                        const lastLine = lines[lines.length - 1];
                        if (lastLine) autoApplyOffersToLine(lastLine);
                    } catch(e) {
                        console.warn("[SpecialOffer] autoApply hook error:", e);
                    }
                    return result;
                },

                // Odoo 19 may use addProduct (camelCase)
                addProduct(product, options) {
                    const result = super.addProduct(product, options);
                    try {
                        const lines = Array.isArray(this.lines) ? this.lines :
                                      this.get_orderlines?.() ||
                                      this.orderlines?.models || [];
                        const lastLine = lines[lines.length - 1];
                        if (lastLine) autoApplyOffersToLine(lastLine);
                    } catch(e) {
                        console.warn("[SpecialOffer] autoApply hook error:", e);
                    }
                    return result;
                },
            });

            console.log("[SpecialOffer] ✅ PosOrder patched for auto-apply at:", path);
            return true;
        } catch(e) {
            console.warn("[SpecialOffer] PosOrder patch failed for:", path, e);
        }
    }
    return false;
}

// Try patching — PosOrder is loaded before our module
if (!tryPatchPosOrder()) {
    setTimeout(() => {
        if (!tryPatchPosOrder()) {
            console.warn("[SpecialOffer] ⚠️ Could not patch PosOrder for auto-apply.");
        }
    }, 0);
}
