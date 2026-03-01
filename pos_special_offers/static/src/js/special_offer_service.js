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
                console.log("[SpecialOffers] Loaded", activeOffers.length, "offers");
            } catch (e) {
                console.warn("[SpecialOffers] Load failed:", e);
                activeOffers = [];
            }
        }

        await loadOffers();

        return {
            getActiveOffers: () => activeOffers,
            refresh: () => loadOffers(),
            getDiscountedPrice(productId, categoryIds, basePrice) {
                for (const offer of activeOffers) {
                    const mp = offer.product_ids.includes(productId);
                    const mc = categoryIds && categoryIds.some(cid => offer.category_ids.includes(cid));
                    if ((mp || mc) && offer.offer_type === 'flat_discount') {
                        const price = offer.discount_type === 'percentage'
                            ? basePrice * (1 - offer.discount_value / 100)
                            : offer.discount_value;
                        return { price, offerName: offer.name };
                    }
                }
                return null;
            },
            applyCoupon(code, productId, categoryIds, basePrice) {
                const offer = activeOffers.find(
                    o => o.offer_type === 'coupon' &&
                         o.coupon_code.toLowerCase() === (code || '').toLowerCase() &&
                         (o.product_ids.includes(productId) ||
                          (categoryIds && categoryIds.some(cid => o.category_ids.includes(cid))))
                );
                if (!offer) return null;
                const price = offer.discount_type === 'percentage'
                    ? basePrice * (1 - offer.discount_value / 100)
                    : offer.discount_value;
                return { price, offerName: offer.name };
            },
        };
    },
};

registry.category("services").add("special_offer_service", specialOfferService);
