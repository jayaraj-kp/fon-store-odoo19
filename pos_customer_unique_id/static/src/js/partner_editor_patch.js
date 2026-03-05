/** @odoo-module **/

/**
 * POS Customer Unique ID – PartnerEditor patch (Odoo 19 compatible)
 *
 * Uses a dynamic registry-based approach so the patch won't crash the POS
 * even if the PartnerEditor component path changes between Odoo versions.
 */

import { patch } from "@web/core/utils/patch";

function applyPartnerEditorPatch(PartnerEditor) {
    patch(PartnerEditor.prototype, {

        get isNewPartner() {
            return !(this.props.partner && this.props.partner.id);
        },

        get shopCode() {
            try {
                return (this.pos && this.pos.config && this.pos.config.shop_code) || '';
            } catch (e) { return ''; }
        },

        get displayPosUniqueId() {
            try {
                if (!this.isNewPartner && this.props.partner && this.props.partner.pos_unique_id) {
                    return this.props.partner.pos_unique_id;
                }
                if (this.isNewPartner && this.shopCode) {
                    return `${this.shopCode.toUpperCase()} - (auto)`;
                }
            } catch (e) { /* silent */ }
            return '';
        },

        async savePartner() {
            const isNew = this.isNewPartner;
            let configId = null;
            try {
                if (isNew && this.pos && this.pos.config && this.pos.config.id) {
                    configId = this.pos.config.id;
                }
            } catch (e) { /* silent */ }

            if (isNew && configId) {
                const originalCall = this.orm.call.bind(this.orm);
                this.orm.call = async (model, method, args, kwargs) => {
                    if (model === 'res.partner' && method === 'create_from_ui') {
                        const partnerArg = args && args[0];
                        if (partnerArg && typeof partnerArg === 'object' && !partnerArg.id) {
                            partnerArg.pos_config_id_for_uid = configId;
                        }
                    }
                    return originalCall(model, method, args, kwargs);
                };
                try {
                    return await super.savePartner(...arguments);
                } finally {
                    this.orm.call = originalCall;
                }
            }
            return super.savePartner(...arguments);
        },
    });
    console.info("[POS Customer UID] PartnerEditor patched successfully.");
}

// ── Try to load PartnerEditor from Odoo's module loader ──────────────────────
// We wait for the POS app to be ready, then locate PartnerEditor dynamically.
// This avoids hard-coding an import path that can change between Odoo versions.

function tryPatchFromLoader() {
    const loader = odoo && odoo.loader;
    if (!loader) return false;

    // Known module paths across Odoo versions
    const candidates = [
        "@point_of_sale/app/screens/partner_list/partner_editor",
        "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor",
    ];

    for (const path of candidates) {
        try {
            const mod = loader.modules.get(path);
            if (mod && mod.PartnerEditor) {
                applyPartnerEditorPatch(mod.PartnerEditor);
                return true;
            }
        } catch (e) { /* try next */ }
    }
    return false;
}

// Attempt patch immediately (works if module already loaded)
if (!tryPatchFromLoader()) {
    // Retry after a short delay (POS lazy-loads components)
    setTimeout(() => {
        if (!tryPatchFromLoader()) {
            console.warn(
                "[POS Customer UID] PartnerEditor not found via loader – " +
                "customer IDs will still be generated server-side when contacts are saved."
            );
        }
    }, 1000);
}
