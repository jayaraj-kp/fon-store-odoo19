/** @odoo-module **/
import { registry } from "@web/core/registry";

const specialOfferService = {
    dependencies: ["orm"],
    async start(env, { orm }) {
        let activeOffers = [];

        async function loadOffers() {
            try {
                activeOffers = await orm.call(
                    "pos.special.offer",
                    "get_active_offers_for_pos",
                    []
                );
                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers", activeOffers);
            } catch (e) {
                console.warn("[SpecialOffers] Load failed:", e);
                activeOffers = [];
            }
        }

        await loadOffers();

        return {
            getActiveOffers: () => activeOffers,
            refresh: () => loadOffers(),
        };
    },
};

registry.category("services").add("special_offer_service", specialOfferService);
