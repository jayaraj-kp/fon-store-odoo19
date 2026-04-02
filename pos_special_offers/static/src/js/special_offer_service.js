/** @odoo-module **/
import { registry } from "@web/core/registry";
import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";

const specialOfferService = {
    dependencies: ["orm"],   // no "pos" dependency — POS config not ready at service start

    async start(env, { orm }) {
        let activeOffers = [];

        // Resolve warehouse_id whether it arrives as integer or object
        function resolveWarehouseId(raw) {
            if (!raw) return null;
            if (typeof raw === "object" && raw.id) return raw.id;
            if (typeof raw === "number" && raw > 0) return raw;
            return null;
        }

        // warehouseId MUST be passed by the caller (button / popup component)
        // because those components use usePos() which is always ready.
        async function loadOffers(warehouseId = null) {
            try {
                const resolvedId = resolveWarehouseId(warehouseId);
                console.log("[SpecialOffers] Loading offers for warehouseId =", resolvedId);

                activeOffers = await orm.call(
                    "pos.special.offer",
                    "get_active_offers_for_pos",
                    [],
                    { warehouse_id: resolvedId }
                );

                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers");
            } catch (e) {
                console.warn("[SpecialOffers] Load failed:", e);
                activeOffers = [];
            }
        }

        // Do NOT load on service start — POS config is not ready yet at this point.
        // The button component calls refresh() with the correct warehouseId
        // the moment the cashier opens the Offers popup.

        const service = {
            getActiveOffers: () => activeOffers,
            // Always pass this.pos.config.warehouse_id from the calling component
            refresh: (warehouseId = null) => loadOffers(warehouseId),
        };

        registerAutoApplyService(service);
        return service;
    },
};

registry.category("services").add("special_offer_service", specialOfferService);


///** @odoo-module **/
//import { registry } from "@web/core/registry";
//import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";
//
//const specialOfferService = {
//    dependencies: ["orm"],
//    async start(env, { orm }) {
//        let activeOffers = [];
//
//        async function loadOffers() {
//            try {
//                activeOffers = await orm.call(
//                    "pos.special.offer",
//                    "get_active_offers_for_pos",
//                    []
//                );
//                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers", activeOffers);
//            } catch (e) {
//                console.warn("[SpecialOffers] Load failed:", e);
//                activeOffers = [];
//            }
//        }
//
//        await loadOffers();
//
//        const service = {
//            getActiveOffers: () => activeOffers,
//            refresh: () => loadOffers(),
//        };
//
//        // Register service reference for auto-apply (direct reference, no owl.__apps__ needed)
//        registerAutoApplyService(service);
//
//        return service;
//    },
//};
//
//registry.category("services").add("special_offer_service", specialOfferService);
