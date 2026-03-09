/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

// ─── 1. CreateContactPopup ───────────────────────────────────────────────────

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
        const v = { name: this.state.name.trim(), customer_rank: 1, type: this.state.contactType };
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

// ─── 2. Global dialog helper ─────────────────────────────────────────────────
// Store dialog service ref when any patched component mounts
let _dialogService = null;
let _posStore = null;

// ─── 3. Patch CustomerList ────────────────────────────────────────────────────

function tryPatch() {
    let CL = null;
    try {
        odoo.loader.modules.forEach((mod) => {
            if (!CL && mod?.CustomerList) CL = mod.CustomerList;
        });
    } catch (e) {}

    if (!CL) return false;
    if (CL.__cash_patched__) return true;
    CL.__cash_patched__ = true;

    patch(CL.prototype, {
        setup() {
            super.setup(...arguments);
            this._cashDialog = useService("dialog");
            _dialogService = this._cashDialog;
            _posStore = this.pos;

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

        async createCustomer() {
            console.log("[pos_cash_customer] createCustomer() called ✅");
            await _openCreatePopup(this);
        },

        // Some Odoo 19 builds use this method name instead
        async newCustomer() {
            console.log("[pos_cash_customer] newCustomer() called ✅");
            await _openCreatePopup(this);
        },
    });

    console.log("[pos_cash_customer] ✅ CustomerList patched. Methods: createCustomer, newCustomer");
    return true;
}

async function _openCreatePopup(ctx) {
    const dialog = ctx._cashDialog || _dialogService;
    if (!dialog) {
        console.error("[pos_cash_customer] No dialog service available");
        return;
    }
    const result = await new Promise((resolve) => {
        dialog.add(CreateContactPopup, { close: resolve });
    });
    if (result?.confirmed && result?.payload) {
        const pos = ctx.pos || _posStore;
        pos?.get_order()?.set_partner(result.payload);
        ctx.props?.close?.();
    }
}

// ─── 4. Also intercept DOM click on Create button as fallback ────────────────

function interceptCreateButton() {
    document.addEventListener("click", async (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;

        // Check if it's the Create button inside the customer choose screen
        const isCreateBtn = (
            btn.classList.contains("button-create") ||
            (btn.textContent.trim() === "Create" && btn.closest(".customer-list, .pos-customer-list, [class*='customer']"))
        );

        if (!isCreateBtn) return;
        if (!_dialogService) return;

        console.log("[pos_cash_customer] Create button intercepted via DOM ✅");
        e.stopImmediatePropagation();
        e.preventDefault();

        const result = await new Promise((resolve) => {
            _dialogService.add(CreateContactPopup, { close: resolve });
        });

        if (result?.confirmed && result?.payload && _posStore) {
            _posStore.get_order()?.set_partner(result.payload);
            // Close the customer list by clicking Discard
            const discard = document.querySelector(".customer-list button.discard, button.btn-discard, [class*='customer'] button:last-child");
            if (discard) discard.click();
        }
    }, true); // capture phase - runs before Odoo's handler
}

// ─── 5. Boot ──────────────────────────────────────────────────────────────────

interceptCreateButton(); // Always intercept as safety net

if (!tryPatch()) {
    [100, 500, 1500, 3000].forEach((d) => setTimeout(tryPatch, d));
}
