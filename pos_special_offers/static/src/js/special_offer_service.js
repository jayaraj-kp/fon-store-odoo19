/** @odoo-module **/
import { registry } from "@web/core/registry";
import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";

const specialOfferService = {
    dependencies: ["orm", "pos"],

    async start(env, { orm, pos }) {
        let activeOffers = [];

        async function loadOffers() {
            try {
                // The POS config always knows which warehouse it belongs to.
                // We pass this to the server so it can filter warehouse-restricted
                // offers correctly — no guessing from session lookups needed.
                const warehouseId = pos?.config?.warehouse_id?.id ?? null;

                activeOffers = await orm.call(
                    "pos.special.offer",
                    "get_active_offers_for_pos",
                    [],                          // positional args (none)
                    { warehouse_id: warehouseId } // keyword arg → Python param
                );

                console.log(
                    "[SpecialOffers] Loaded", activeOffers.length,
                    "offers for warehouse_id =", warehouseId,
                    activeOffers
                );
            } catch (e) {
                console.warn("[SpecialOffers] Load failed:", e);
                activeOffers = [];
            }
        }

        await loadOffers();

        const service = {
            getActiveOffers: () => activeOffers,
            refresh: () => loadOffers(),
        };

        // Register service reference for auto-apply
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
