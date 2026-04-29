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
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";

const specialOfferService = {
    // ✅ FIX: add "pos" to dependencies so PosStore is fully initialised
    //         before this service starts. Without this, env.services.pos
    //         is null at start-time and posConfigId is always null,
    //         which causes the server to skip warehouse filtering and
    //         return every offer to every POS session.
    dependencies: ["orm", "pos"],

    async start(env, { orm, pos }) {
        let activeOffers = [];

        async function loadOffers() {
            try {
                // ✅ FIX: read config id directly from the injected `pos`
                //         service — it is guaranteed to be ready now.
                const posConfigId =
                    pos?.config?.id ??
                    pos?.pos_session?.config_id?.[0] ??
                    pos?.config_id ??
                    null;

                activeOffers = await orm.call(
                    "pos.special.offer",
                    "get_active_offers_for_pos",
                    [],
                    { pos_config_id: posConfigId }
                );
                console.log(
                    "[SpecialOffers] Loaded", activeOffers.length, "offers",
                    "(config id:", posConfigId, ")", activeOffers
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

        registerAutoApplyService(service);
        return service;
    },
};

registry.category("services").add("special_offer_service", specialOfferService);