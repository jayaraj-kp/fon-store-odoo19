/** @odoo-module **/
import { registry } from "@web/core/registry";
import { registerAutoApplyService } from "@pos_special_offers/js/special_offer_auto_apply";

const specialOfferService = {
    // Add pos_store as a dependency so it is fully initialised before we run
    dependencies: ["orm", "pos_store"],

    async start(env, { orm, pos_store }) {
        let activeOffers = [];

        /**
         * Read the warehouse_id from the POS store.
         *
         * In Odoo 19 CE the pos_store service exposes the loaded models directly.
         * pos.config is loaded into pos_store.config (a single record object).
         * Its warehouse_id field is a Many2one stored as an object { id, name }
         * or as a plain integer depending on whether it was fully loaded.
         *
         * We try every known path so this stays robust across minor version changes.
         */
        function getPosWarehouseId() {
            try {
                // ── Path 1: pos_store.config.warehouse_id  (Odoo 17/18/19 standard) ──
                const cfg = pos_store?.config;
                if (cfg) {
                    const wh = cfg.warehouse_id;
                    if (wh) {
                        const id = typeof wh === "object" ? (wh.id ?? wh[0]) : wh;
                        if (id) {
                            console.log("[SpecialOffers] warehouse_id from config.warehouse_id:", id);
                            return id;
                        }
                    }
                }

                // ── Path 2: pos_store.session.warehouse_id ────────────────────────────
                const session = pos_store?.session;
                if (session) {
                    const wh = session.warehouse_id;
                    if (wh) {
                        const id = typeof wh === "object" ? (wh.id ?? wh[0]) : wh;
                        if (id) {
                            console.log("[SpecialOffers] warehouse_id from session.warehouse_id:", id);
                            return id;
                        }
                    }
                }

                // ── Path 3: models store — pos.config record ──────────────────────────
                const models = pos_store?.models;
                if (models) {
                    const configModel = models["pos.config"];
                    if (configModel) {
                        const configs = typeof configModel.getAll === "function"
                            ? configModel.getAll()
                            : Object.values(configModel).filter(r => r?.id);
                        if (configs.length > 0) {
                            const wh = configs[0].warehouse_id;
                            if (wh) {
                                const id = typeof wh === "object" ? (wh.id ?? wh[0]) : wh;
                                if (id) {
                                    console.log("[SpecialOffers] warehouse_id from models[pos.config]:", id);
                                    return id;
                                }
                            }
                        }
                    }
                }

                // ── Debug: log what pos_store looks like so we can add the right path ─
                console.warn(
                    "[SpecialOffers] warehouse_id not found. pos_store keys:",
                    Object.keys(pos_store || {})
                );
                if (cfg) {
                    console.warn("[SpecialOffers] config keys:", Object.keys(cfg));
                    console.warn("[SpecialOffers] config.warehouse_id raw value:", cfg.warehouse_id);
                }

            } catch (e) {
                console.warn("[SpecialOffers] Error reading warehouse_id:", e);
            }
            return null;
        }

        async function loadOffers() {
            try {
                const warehouseId = getPosWarehouseId();
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
