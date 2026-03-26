
//
///** @odoo-module **/
//
//import { Component, useState } from "@odoo/owl";
//import { usePos } from "@point_of_sale/app/hooks/pos_hook";
//import { useService } from "@web/core/utils/hooks";
//import { patch } from "@web/core/utils/patch";
//import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
//import { Dialog } from "@web/core/dialog/dialog";
//
//const CASH_CUSTOMER_NAME = "CASH CUSTOMER";
//const MIN_CHARS = 3;
//
//// ─────────────────────────────────────────────
////  Create Customer Dialog
//// ─────────────────────────────────────────────
//export class CreateCustomerDialog extends Component {
//    static template = "pos_cash_customer_contact.CreateCustomerDialog";
//    static components = { Dialog };
//    static props = {
//        phone: { type: String, default: "" },
//        autoTag: { type: Object, optional: true },  // { id, name } of the matched tag
//        onCreated: Function,
//        close: Function,
//    };
//
//    setup() {
//        this.orm = useService("orm");
//        this.notification = useService("notification");
//
//        const query = this.props.phone || "";
//        const digitsOnly = query.replace(/\D/g, "");
//        const isPhone = /^\d+$/.test(digitsOnly) && digitsOnly.length >= 3;
//
//        this.form = useState({
//            name: query,
//            phone: isPhone ? query : "",
//            mobile: "",
//            email: "",
//            // pre-select the tag if one was resolved
//            tagId: this.props.autoTag ? this.props.autoTag.id : false,
//            tagName: this.props.autoTag ? this.props.autoTag.name : "",
//            saving: false,
//            error: "",
//        });
//    }
//
//    async onSave() {
//        this.form.error = "";
//
//        if (!this.form.name.trim()) {
//            this.form.error = "Name is required.";
//            return;
//        }
//
//        const phoneVal = this.form.phone.trim();
//        if (phoneVal) {
//            const digits = phoneVal.replace(/\D/g, "");
//            if (digits.length !== 10) {
//                this.form.error = "Please enter 10 digit mobile number.";
//                return;
//            }
//        }
//
//        const mobileVal = this.form.mobile.trim();
//        if (mobileVal) {
//            const mDigits = mobileVal.replace(/\D/g, "");
//            if (mDigits.length !== 10) {
//                this.form.error = "Please enter 10 digit mobile number";
//                return;
//            }
//        }
//
//        this.form.saving = true;
//
//        try {
//            await this.props.onCreated({
//                name: this.form.name.trim(),
//                phone: this.form.phone.trim(),
//                mobile: this.form.mobile.trim(),
//                email: this.form.email.trim(),
//                tagId: this.form.tagId,
//            });
//            this.props.close();
//        } catch (err) {
//            this.form.error = err.message || "Could not save customer.";
//            this.form.saving = false;
//        }
//    }
//
//    onDiscard() {
//        this.props.close();
//    }
//}
//
//// ─────────────────────────────────────────────
////  Phone Customer Bar
//// ─────────────────────────────────────────────
//export class PhoneCustomerBar extends Component {
//    static template = "pos_cash_customer_contact.PhoneCustomerBar";
//    static props = {};
//
//    setup() {
//        this.pos = usePos();
//        this.orm = useService("orm");
//        this.dialog = useService("dialog");
//        this.notification = useService("notification");
//        this.state = useState({
//            query: "",
//            suggestions: [],
//            showDropdown: false,
//            selectedName: "",
//            found: false,
//        });
//    }
//
//    // ── Resolve which tag to auto-assign based on POS config name ──
//    // Matches if the POS name contains the tag name (case-insensitive)
//    async _getAutoTag() {
//        try {
//            const posName = (this.pos.config.name || "").toUpperCase();
//
//            // Load all tags from res.partner.category
//            const tags = await this.orm.searchRead(
//                "res.partner.category",
//                [],
//                ["id", "name"],
//                { limit: 100 }
//            );
//
//            // Find the first tag whose name appears in the POS config name
//            const matched = tags.find(
//                (t) => posName.includes(t.name.toUpperCase())
//            );
//
//            return matched ? { id: matched.id, name: matched.name } : null;
//        } catch (e) {
//            console.warn("Could not resolve auto tag:", e);
//            return null;
//        }
//    }
//
//    _getSuggestions(query) {
//        if (!query || query.length < MIN_CHARS) return [];
//        const q = query.toLowerCase();
//        return this.pos.models["res.partner"]
//            .filter((p) => {
//                if (!p.name) return false;
//                return (
//                    p.name.toLowerCase().includes(q) ||
//                    (p.phone || "").includes(q) ||
//                    (p.mobile || "").includes(q)
//                );
//            })
//            .slice(0, 8);
//    }
//
//    onInput(ev) {
//        const query = ev.target.value;
//        this.state.query = query;
//        this.state.found = false;
//        this.state.selectedName = "";
//
//        if (!query) {
//            this.pos.getOrder().setPartner(false);
//            this.state.suggestions = [];
//            this.state.showDropdown = false;
//            return;
//        }
//
//        const suggestions = this._getSuggestions(query);
//        this.state.suggestions = suggestions;
//        this.state.showDropdown = query.length >= MIN_CHARS;
//
//        const exact = this.pos.models["res.partner"].find(
//            (p) => p.phone === query || p.mobile === query
//        );
//        if (exact) {
//            this.pos.getOrder().setPartner(exact);
//            this.state.found = true;
//            this.state.selectedName = exact.name;
//            this.state.showDropdown = false;
//        } else {
//            this.pos.getOrder().setPartner(false);
//        }
//    }
//
//    onSelectSuggestion(ev, partner) {
//        this.pos.getOrder().setPartner(partner);
//        this.state.query = partner.phone || partner.mobile || partner.name;
//        this.state.selectedName = partner.name;
//        this.state.found = true;
//        this.state.showDropdown = false;
//        this.state.suggestions = [];
//    }
//
//    onClear() {
//        this.state.query = "";
//        this.state.found = false;
//        this.state.selectedName = "";
//        this.state.suggestions = [];
//        this.state.showDropdown = false;
//        this.pos.getOrder().setPartner(false);
//    }
//
//    onBlur() {
//        setTimeout(() => { this.state.showDropdown = false; }, 200);
//    }
//
//    onFocus() {
//        if (this.state.query && this.state.query.length >= MIN_CHARS && !this.state.found) {
//            this.state.showDropdown = true;
//        }
//    }
//
//    async _getCashCustomerParentId() {
//        const results = await this.orm.searchRead(
//            "res.partner",
//            [["name", "=", CASH_CUSTOMER_NAME], ["is_company", "=", true]],
//            ["id"],
//            { limit: 1 }
//        );
//        if (results.length) return results[0].id;
//
//        const newId = await this.orm.create("res.partner", [{
//            name: CASH_CUSTOMER_NAME,
//            is_company: true,
//            customer_rank: 1,
//        }]);
//        return Array.isArray(newId) ? newId[0] : newId;
//    }
//
//    async _doCreate(formData) {
//        const parentId = await this._getCashCustomerParentId();
//
//        const vals = {
//            name: formData.name,
//            phone: formData.phone || false,
//            email: formData.email || false,
//            parent_id: parentId,
//            customer_rank: 1,
//        };
//
//        // Attach the contact tag if resolved
//        if (formData.tagId) {
//            vals.category_id = [[4, formData.tagId]];  // ORM command 4 = link existing
//        }
//
//        const rawId = await this.orm.create("res.partner", [vals]);
//        const partnerId = Array.isArray(rawId) ? rawId[0] : rawId;
//
//        await this.pos.data.searchRead(
//            "res.partner",
//            [["id", "=", partnerId]],
//            [],
//            { load: false }
//        );
//
//        const newPartner = this.pos.models["res.partner"].find(
//            (p) => p.id === partnerId
//        );
//
//        if (newPartner) {
//            this.pos.getOrder().setPartner(newPartner);
//            this.state.query = newPartner.phone || newPartner.name;
//            this.state.found = true;
//            this.state.selectedName = newPartner.name;
//            this.state.showDropdown = false;
//            this.notification.add(
//                `Customer created: ${newPartner.name}`,
//                { type: "success", sticky: false }
//            );
//        }
//    }
//
//    // "Create [query]" quick create from dropdown
//    async onQuickCreate() {
//        this.state.showDropdown = false;
//        const query = this.state.query.trim();
//        if (!query) return;
//
//        const looksLikePhone = /^\d+$/.test(query);
//        if (looksLikePhone && query.replace(/\D/g, "").length !== 10) {
//            this.notification.add(
//                "Phone number must be exactly 10 digits.",
//                { type: "danger", sticky: false }
//            );
//            return;
//        }
//
//        const autoTag = await this._getAutoTag();
//
//        await this._doCreate({
//            name: query,
//            phone: looksLikePhone ? query : "",
//            email: "",
//            tagId: autoTag ? autoTag.id : false,
//        });
//    }
//
//    // "Create and edit..." — open full dialog with tag pre-filled
//    async onCreateAndEdit() {
//        this.state.showDropdown = false;
//        const autoTag = await this._getAutoTag();
//
//        this.dialog.add(CreateCustomerDialog, {
//            phone: this.state.query,
//            autoTag: autoTag,
//            onCreated: async (formData) => {
//                await this._doCreate(formData);
//            },
//        });
//    }
//}
//
//patch(ProductScreen, {
//    components: {
//        ...ProductScreen.components,
//        PhoneCustomerBar,
//    },
//});

/** @odoo-module **/

import { Component, useState, useEffect } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { Dialog } from "@web/core/dialog/dialog";

const CASH_CUSTOMER_NAME = "CASH CUSTOMER";
const MIN_CHARS = 3;

// ─────────────────────────────────────────────
//  Create Customer Dialog
// ─────────────────────────────────────────────
export class CreateCustomerDialog extends Component {
    static template = "pos_cash_customer_contact.CreateCustomerDialog";
    static components = { Dialog };
    static props = {
        phone: { type: String, default: "" },
        autoTag: { type: Object, default: null },
        onCreated: Function,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const query = this.props.phone || "";
        const digitsOnly = query.replace(/\D/g, "");
        const isPhone = /^\d+$/.test(digitsOnly) && digitsOnly.length >= 3;

        this.form = useState({
            name: query,
            phone: isPhone ? query : "",
            email: "",
            saving: false,
            error: "",
            tagId: this.props.autoTag ? this.props.autoTag.id : false,
            tagName: this.props.autoTag ? this.props.autoTag.name : "",
        });

        // Set up keyboard shortcut listener for Alt+C
        useEffect(() => {
            const handleKeyDown = (event) => {
                // Check for Alt+C combination
                if (event.altKey && event.key === 'c') {
                    event.preventDefault();
                    this.onSave();
                }
            };

            document.addEventListener('keydown', handleKeyDown);

            return () => {
                document.removeEventListener('keydown', handleKeyDown);
            };
        });
    }

    async onSave() {
        this.form.error = "";

        if (!this.form.name.trim()) {
            this.form.error = "Name is required.";
            return;
        }

        const phoneVal = this.form.phone.trim();
        if (phoneVal) {
            const digits = phoneVal.replace(/\D/g, "");
            if (digits.length !== 10) {
                this.form.error = "Phone number must be exactly 10 digits.";
                return;
            }
        }

        const emailVal = this.form.email.trim();
        if (emailVal) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailVal)) {
                this.form.error = "Please enter a valid email address.";
                return;
            }
        }

        this.form.saving = true;

        try {
            await this.props.onCreated({
                name: this.form.name.trim(),
                phone: this.form.phone.trim(),
                email: this.form.email.trim(),
                tagId: this.form.tagId,
            });
            this.props.close();
        } catch (err) {
            this.form.error = err.message || "Could not save customer.";
            this.form.saving = false;
        }
    }

    onDiscard() {
        this.props.close();
    }
}

// ─────────────────────────────────────────────
//  Phone Customer Bar
// ─────────────────────────────────────────────
export class PhoneCustomerBar extends Component {
    static template = "pos_cash_customer_contact.PhoneCustomerBar";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            query: "",
            suggestions: [],
            showDropdown: false,
            selectedName: "",
            found: false,
        });
    }

    // ── Resolve which tag to auto-assign based on POS config name ──
    // Matches if the POS name contains the tag name (case-insensitive)
    async _getAutoTag() {
        try {
            const posName = (this.pos.config.name || "").toUpperCase();

            // Load all tags from res.partner.category
            const tags = await this.orm.searchRead(
                "res.partner.category",
                [],
                ["id", "name"],
                { limit: 100 }
            );

            // Find the first tag whose name appears in the POS config name
            const matched = tags.find(
                (t) => posName.includes(t.name.toUpperCase())
            );

            return matched ? { id: matched.id, name: matched.name } : null;
        } catch (e) {
            console.warn("Could not resolve auto tag:", e);
            return null;
        }
    }

    _getSuggestions(query) {
        if (!query || query.length < MIN_CHARS) return [];
        const q = query.toLowerCase();
        return this.pos.models["res.partner"]
            .filter((p) => {
                if (!p.name) return false;
                return (
                    p.name.toLowerCase().includes(q) ||
                    (p.phone || "").includes(q) ||
                    (p.mobile || "").includes(q)
                );
            })
            .slice(0, 8);
    }

    onInput(ev) {
        const query = ev.target.value;
        this.state.query = query;
        this.state.found = false;
        this.state.selectedName = "";

        if (!query) {
            this.pos.getOrder().setPartner(false);
            this.state.suggestions = [];
            this.state.showDropdown = false;
            return;
        }

        const suggestions = this._getSuggestions(query);
        this.state.suggestions = suggestions;
        this.state.showDropdown = query.length >= MIN_CHARS;

        const exact = this.pos.models["res.partner"].find(
            (p) => p.phone === query || p.mobile === query
        );
        if (exact) {
            this.pos.getOrder().setPartner(exact);
            this.state.found = true;
            this.state.selectedName = exact.name;
            this.state.showDropdown = false;
        } else {
            this.pos.getOrder().setPartner(false);
        }
    }

    onSelectSuggestion(ev, partner) {
        this.pos.getOrder().setPartner(partner);
        this.state.query = partner.phone || partner.mobile || partner.name;
        this.state.selectedName = partner.name;
        this.state.found = true;
        this.state.showDropdown = false;
        this.state.suggestions = [];
    }

    onClear() {
        this.state.query = "";
        this.state.found = false;
        this.state.selectedName = "";
        this.state.suggestions = [];
        this.state.showDropdown = false;
        this.pos.getOrder().setPartner(false);
    }

    onBlur() {
        setTimeout(() => { this.state.showDropdown = false; }, 200);
    }

    onFocus() {
        if (this.state.query && this.state.query.length >= MIN_CHARS && !this.state.found) {
            this.state.showDropdown = true;
        }
    }

    async _getCashCustomerParentId() {
        const results = await this.orm.searchRead(
            "res.partner",
            [["name", "=", CASH_CUSTOMER_NAME], ["is_company", "=", true]],
            ["id"],
            { limit: 1 }
        );
        if (results.length) return results[0].id;

        const newId = await this.orm.create("res.partner", [{
            name: CASH_CUSTOMER_NAME,
            is_company: true,
            customer_rank: 1,
        }]);
        return Array.isArray(newId) ? newId[0] : newId;
    }

    async _doCreate(formData) {
        const parentId = await this._getCashCustomerParentId();

        const vals = {
            name: formData.name,
            phone: formData.phone || false,
            email: formData.email || false,
            parent_id: parentId,
            customer_rank: 1,
        };

        // Attach the contact tag if resolved
        if (formData.tagId) {
            vals.category_id = [[4, formData.tagId]];  // ORM command 4 = link existing
        }

        const rawId = await this.orm.create("res.partner", [vals]);
        const partnerId = Array.isArray(rawId) ? rawId[0] : rawId;

        await this.pos.data.searchRead(
            "res.partner",
            [["id", "=", partnerId]],
            [],
            { load: false }
        );

        const newPartner = this.pos.models["res.partner"].find(
            (p) => p.id === partnerId
        );

        if (newPartner) {
            this.pos.getOrder().setPartner(newPartner);
            this.state.query = newPartner.phone || newPartner.name;
            this.state.found = true;
            this.state.selectedName = newPartner.name;
            this.state.showDropdown = false;
            this.notification.add(
                `Customer created: ${newPartner.name}`,
                { type: "success", sticky: false }
            );
        }
    }

    // "Create [query]" quick create from dropdown
    async onQuickCreate() {
        this.state.showDropdown = false;
        const query = this.state.query.trim();
        if (!query) return;

        const looksLikePhone = /^\d+$/.test(query);
        if (looksLikePhone && query.replace(/\D/g, "").length !== 10) {
            this.notification.add(
                "Phone number must be exactly 10 digits.",
                { type: "danger", sticky: false }
            );
            return;
        }

        const autoTag = await this._getAutoTag();

        await this._doCreate({
            name: query,
            phone: looksLikePhone ? query : "",
            email: "",
            tagId: autoTag ? autoTag.id : false,
        });
    }

    // "Create and edit..." — open full dialog with tag pre-filled
    async onCreateAndEdit() {
        this.state.showDropdown = false;
        const autoTag = await this._getAutoTag();

        this.dialog.add(CreateCustomerDialog, {
            phone: this.state.query,
            autoTag: autoTag,
            onCreated: async (formData) => {
                await this._doCreate(formData);
            },
        });
    }
}

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        PhoneCustomerBar,
    },
});
