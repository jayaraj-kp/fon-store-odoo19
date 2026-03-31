/** @odoo-module **/
import { registry } from "@web/core/registry";
import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";

const specialOfferService = {
    // Only orm is needed — we fetch warehouse_id from the server via pos.config
    dependencies: ["orm"],

    async start(env, { orm }) {
        let activeOffers = [];

        /**
         * Ask the server for the warehouse_id of the current POS session.
         *
         * The backend method get_current_pos_warehouse_id() reads
         * the active pos.session → pos.config → warehouse_id for the
         * currently logged-in user. This is the most reliable approach
         * in Odoo 19 CE because pos_store is not a named service.
         */
        async function fetchWarehouseId() {
            try {
                const result = await orm.call(
                    "pos.special.offer",
                    "get_current_pos_warehouse_id",
                    []
                );
                console.log("[SpecialOffers] Fetched warehouse_id from server:", result);
                return result || null;
            } catch (e) {
                console.warn("[SpecialOffers] Could not fetch warehouse_id:", e);
                return null;
            }
        }

        async function loadOffers() {
            try {
                const warehouseId = await fetchWarehouseId();
                console.log("[SpecialOffers] Loading offers for warehouse_id:", warehouseId);
                activeOffers = await orm.call(
                    "pos.special.offer",
                    "get_active_offers_for_pos",
                    [],
                    { warehouse_id: warehouseId }
                );
                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers", activeOffers);
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
//        /**
//         * Resolve the warehouse_id from the POS session/config.
//         * pos.config has a warehouse_id field in Odoo standard.
//         * We try several paths to stay compatible across Odoo 17/18/19.
//         */
//        function getPosWarehouseId() {
//            try {
//                // Odoo 19 POS — env.services.pos_store or similar
//                const posStore = env.services?.pos_store ?? env.pos;
//                if (!posStore) return null;
//
//                // Path 1: config.warehouse_id (most common in Odoo 17+)
//                const cfg = posStore.config ?? posStore.pos_session?.config_id;
//                if (cfg) {
//                    const wh = cfg.warehouse_id;
//                    if (wh) return typeof wh === "object" ? wh.id : wh;
//                }
//
//                // Path 2: session.warehouse_id (some Odoo versions expose it here)
//                const session = posStore.session ?? posStore.pos_session;
//                if (session?.warehouse_id) {
//                    const wh = session.warehouse_id;
//                    return typeof wh === "object" ? wh.id : wh;
//                }
//            } catch (e) {
//                console.warn("[SpecialOffers] Could not resolve warehouse_id:", e);
//            }
//            return null;
//        }
//
//        async function loadOffers() {
//            try {
//                const warehouseId = getPosWarehouseId();
//                console.log("[SpecialOffers] Loading offers for warehouse_id:", warehouseId);
//                activeOffers = await orm.call(
//                    "pos.special.offer",
//                    "get_active_offers_for_pos",
//                    [],
//                    { warehouse_id: warehouseId }
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
//        // Register service reference for auto-apply
//        registerAutoApplyService(service);
//
//        return service;
//    },
//};
//
//registry.category("services").add("special_offer_service", specialOfferService);
//
//
/////** @odoo-module **/
////import { registry } from "@web/core/registry";
////import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";
////
////const specialOfferService = {
////    dependencies: ["orm"],
////    async start(env, { orm }) {
////        let activeOffers = [];
////
////        async function loadOffers() {
////            try {
////                activeOffers = await orm.call(
////                    "pos.special.offer",
////                    "get_active_offers_for_pos",
////                    []
////                );
////                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers", activeOffers);
////            } catch (e) {
////                console.warn("[SpecialOffers] Load failed:", e);
////                activeOffers = [];
////            }
////        }
////
////        await loadOffers();
////
////        const service = {
////            getActiveOffers: () => activeOffers,
////            refresh: () => loadOffers(),
////        };
////
////        // Register service reference for auto-apply (direct reference, no owl.__apps__ needed)
////        registerAutoApplyService(service);
////
////        return service;
////    },
////};
////
////registry.category("services").add("special_offer_service", specialOfferService);
