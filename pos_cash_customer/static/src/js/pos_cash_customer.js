/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// ─── CreateContactPopup ──────────────────────────────────────────────────────

class CreateContactPopup extends Component {
    static template = "pos_cash_customer.CreateContactPopup";
    static props = { title: { type: String, optional: true }, close: Function };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            contactType: "contact",
            name: "", email: "", phone: "",
            street: "", street2: "", city: "", zip: "", country: "",
            notes: "", saving: false, error: "",
        });
    }

    setContactType(type) { this.state.contactType = type; }
    getTabClass(type) {
        return "contact-type-tab" + (this.state.contactType === type ? " active" : "");
    }

    async saveAndClose() {
        if (!this.state.name.trim()) { this.state.error = "Name is required."; return; }
        this.state.error = ""; this.state.saving = true;
        try {
            const p = await this._save();
            this.props.close({ confirmed: true, payload: p });
        } catch (e) {
            this.state.error = "Error saving. Please try again.";
        } finally { this.state.saving = false; }
    }

    async saveAndNew() {
        if (!this.state.name.trim()) { this.state.error = "Name is required."; return; }
        this.state.error = ""; this.state.saving = true;
        try {
            await this._save();
            Object.assign(this.state, {
                name: "", email: "", phone: "", street: "", street2: "",
                city: "", zip: "", country: "", notes: "", saving: false, error: "",
            });
        } catch (e) {
            this.state.error = "Error saving."; this.state.saving = false;
        }
    }

    discard() { this.props.close({ confirmed: false, payload: null }); }

    async _save() {
        const v = {
            name: this.state.name.trim(), customer_rank: 1,
            type: this.state.contactType || "contact"
        };
        if (this.state.email)   v.email   = this.state.email.trim();
        if (this.state.phone)   v.phone   = this.state.phone.trim();
        if (this.state.street)  v.street  = this.state.street.trim();
        if (this.state.street2) v.street2 = this.state.street2.trim();
        if (this.state.city)    v.city    = this.state.city.trim();
        if (this.state.zip)     v.zip     = this.state.zip.trim();
        if (this.state.notes)   v.comment = this.state.notes.trim();
        const r = await this.orm.call("res.partner", "create_from_pos_simplified", [v]);
        return r?.id ? { id: r.id, name: r.name, phone: r.phone || "" } : null;
    }
}

// ─── Globals ─────────────────────────────────────────────────────────────────
let _dialog = null;
let _pos = null;

// ─── Patch CustomerList ───────────────────────────────────────────────────────
function tryPatch() {
    let CL = null;
    try {
        odoo.loader.modules.forEach((mod) => {
            if (!CL && mod?.CustomerList) CL = mod.CustomerList;
        });
    } catch (e) {}

    if (!CL || CL.__cash_patched__) return !!CL;
    CL.__cash_patched__ = true;

    patch(CL.prototype, {
        setup() {
            super.setup(...arguments);
            this._cashDialog = useService("dialog");
            _dialog = this._cashDialog;
            _pos = this.pos;

            onMounted(() => {
                try {
                    const order = this.pos.get_order();
                    if (!order || order.get_partner()) return;
                    const id = this.pos.config.cash_customer_id;
                    if (!id) return;
                    const found = this.pos.models["res.partner"]?.find((p) => p.id === id);
                    if (found) order.set_partner(found);
                } catch (e) { console.warn("[pos_cash_customer] default:", e); }
            });
        },

        // Patch the method the console trace shows: editPartner
        editPartner(partner) {
            // editPartner(null/undefined) = Create new
            // editPartner(existingPartner) = Edit existing - let it through normally
            if (partner) {
                console.log("[pos_cash_customer] editPartner(existing) - letting through");
                return super.editPartner(partner);
            }
            console.log("[pos_cash_customer] editPartner(null) = Create → opening popup ✅");
            _openPopup(this);
        },

        // Also patch createCustomer in case it's used
        async createCustomer() {
            console.log("[pos_cash_customer] createCustomer() ✅");
            await _openPopup(this);
        },
    });

    console.log("[pos_cash_customer] ✅ CustomerList patched (editPartner + createCustomer)");
    return true;
}

async function _openPopup(ctx) {
    const dlg = ctx._cashDialog || _dialog;
    if (!dlg) { console.error("[pos_cash_customer] no dialog service"); return; }

    const result = await new Promise((resolve) => {
        dlg.add(CreateContactPopup, { close: resolve });
    });

    if (result?.confirmed && result?.payload) {
        const pos = ctx.pos || _pos;
        pos?.get_order()?.set_partner(result.payload);
        ctx.props?.close?.();
    }
}

if (!tryPatch()) {
    [100, 500, 1500, 3000].forEach((d) => setTimeout(tryPatch, d));
}
