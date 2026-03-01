/** @odoo-module **/

import { registry } from "@web/core/registry";

export const specialOfferService = {
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
            } catch (e) {
                console.warn("[SpecialOffers] Could not load offers:", e);
                activeOffers = [];
            }
        }

        await loadOffers();

        return {
            getActiveOffers() {
                return activeOffers;
            },
            async refresh() {
                await loadOffers();
            },
            getDiscountedPrice(productId, categoryId, basePrice) {
                for (const offer of activeOffers) {
                    const matchesProduct = offer.product_ids.includes(productId);
                    const matchesCategory = categoryId && offer.category_ids.includes(categoryId);
                    if (matchesProduct || matchesCategory) {
                        if (offer.discount_type === "percentage") {
                            return {
                                price: basePrice * (1 - offer.discount_value / 100),
                                offerName: offer.name,
                            };
                        } else {
                            return {
                                price: offer.discount_value,
                                offerName: offer.name,
                            };
                        }
                    }
                }
                return null;
            },
        };
    },
};

registry.category("services").add("special_offer_service", specialOfferService);
