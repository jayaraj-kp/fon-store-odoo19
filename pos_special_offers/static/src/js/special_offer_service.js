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
    dependencies: ["orm"],
    async start(env, { orm }) {
        let activeOffers = [];

        async function loadOffers() {
            try {
                // Resolve the current POS config id so the server can apply
                // warehouse filtering.  Works for Odoo 17 / 18 / 19 POS.
                let posConfigId = null;
                try {
                    // The PosStore is available on the env after it is initialised.
                    // Try the most common paths used across Odoo versions.
                    const posStore = env.services?.pos ?? env.pos ?? null;
                    if (posStore) {
                        posConfigId =
                            posStore.config?.id ??
                            posStore.pos_session?.config_id?.[0] ??
                            posStore.config_id ??
                            null;
                    }
                } catch (e) {
                    // Not critical — server will return all active offers if
                    // the config id is unknown (global offers still work).
                    console.warn("[SpecialOffers] Could not resolve pos_config_id:", e);
                }

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

        // Register service reference for auto-apply
        registerAutoApplyService(service);

        return service;
    },
};

registry.category("services").add("special_offer_service", specialOfferService);