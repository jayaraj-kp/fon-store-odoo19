/** @odoo-module **/

/**
 * POS Customer Unique ID – PartnerEditor patch
 *
 * What this does:
 *  1. When saving a NEW partner from POS, injects `pos_config_id_for_uid`
 *     into the data sent to the server so the Python side can generate
 *     the correct shop-prefixed ID (e.g. CHL - 00001).
 *  2. Exposes `pos_unique_id` inside the PartnerEditor state so the
 *     OWL template can render the badge.
 *  3. After a new partner is saved and the POS reloads the partner record,
 *     the generated ID is automatically shown.
 */

import { PartnerEditor } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { patch } from "@web/core/utils/patch";

patch(PartnerEditor.prototype, {

    // ── Setup ─────────────────────────────────────────────────────────────
    setup() {
        super.setup(...arguments);
        // Expose pos_unique_id from the current partner prop (if editing)
        // For new partners it will be empty and populated after reload.
    },

    // ── Helpers ───────────────────────────────────────────────────────────

    /**
     * Returns true if we are creating a brand-new partner (no id yet).
     */
    get isNewPartner() {
        return !(this.props.partner && this.props.partner.id);
    },

    /**
     * Returns the shop code from the current POS config, or empty string.
     */
    get shopCode() {
        return (this.pos && this.pos.config && this.pos.config.shop_code) || '';
    },

    /**
     * Returns the auto-generated pos_unique_id of the currently-open partner,
     * or a preview hint for new partners.
     */
    get displayPosUniqueId() {
        if (!this.isNewPartner && this.props.partner && this.props.partner.pos_unique_id) {
            return this.props.partner.pos_unique_id;
        }
        if (this.isNewPartner && this.shopCode) {
            return `${this.shopCode.toUpperCase()} - (auto)`;
        }
        return '';
    },

    // ── Override save to inject our config ID ────────────────────────────

    /**
     * Patch the internal method that builds the partner data object
     * before it is sent to `res.partner.create_from_ui`.
     *
     * We inject `pos_config_id_for_uid` so the Python override can
     * identify which shop's sequence to use.
     */
    getPartnerData() {
        // Some Odoo versions have getPartnerData(), others build it inline.
        // We try to call super; if it doesn't exist we return undefined.
        let data;
        try {
            data = super.getPartnerData(...arguments);
        } catch (e) {
            data = undefined;
        }

        if (data && this.isNewPartner && this.pos && this.pos.config && this.pos.config.id) {
            data.pos_config_id_for_uid = this.pos.config.id;
        }
        return data;
    },

    /**
     * Main save override – works whether the version uses getPartnerData()
     * or builds the partner object directly inside savePartner().
     */
    async savePartner() {
        const isNew = this.isNewPartner;

        // For Odoo versions that don't use getPartnerData(), we monkey-patch
        // the ORM call temporarily to inject our extra field.
        if (isNew && this.pos && this.pos.config && this.pos.config.id) {
            const originalOrmCall = this.orm.call.bind(this.orm);
            const configId = this.pos.config.id;

            this.orm.call = async (model, method, args, kwargs) => {
                // Intercept only the create_from_ui call for res.partner
                if (model === 'res.partner' && method === 'create_from_ui') {
                    const partnerArg = args && args[0];
                    if (partnerArg && typeof partnerArg === 'object') {
                        // Only inject for new partners (no id field or id is falsy)
                        if (!partnerArg.id) {
                            partnerArg.pos_config_id_for_uid = configId;
                        }
                    }
                }
                return originalOrmCall(model, method, args, kwargs);
            };

            try {
                return await super.savePartner(...arguments);
            } finally {
                // Always restore the original orm.call
                this.orm.call = originalOrmCall;
            }
        }

        return super.savePartner(...arguments);
    },
});
