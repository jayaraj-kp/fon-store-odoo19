/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class CreateContactPopup extends Component {
    static template = "pos_cash_customer.CreateContactPopup";
    static props = {
        title: { type: String, optional: true },
        close: Function,
    };
    static defaultProps = {
        title: "Create Contact",
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");

        this.state = useState({
            contactType: "contact",
            name: "",
            email: "",
            phone: "",
            street: "",
            street2: "",
            city: "",
            zip: "",
            country: "",
            gstin: "",
            notes: "",
            saving: false,
            error: "",
        });
    }

    setContactType(type) {
        this.state.contactType = type;
    }

    getTabClass(type) {
        return this.state.contactType === type
            ? "contact-type-tab active"
            : "contact-type-tab";
    }

    async saveAndClose() {
        if (!this.state.name.trim()) {
            this.state.error = "Name is required.";
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            const partner = await this._savePartner();
            this.props.close({ confirmed: true, payload: partner });
        } catch (e) {
            this.state.error = "Error saving contact. Please try again.";
            console.error("[pos_cash_customer]", e);
        } finally {
            this.state.saving = false;
        }
    }

    async saveAndNew() {
        if (!this.state.name.trim()) {
            this.state.error = "Name is required.";
            return;
        }
        this.state.error = "";
        this.state.saving = true;
        try {
            await this._savePartner();
            Object.assign(this.state, {
                name: "", email: "", phone: "", street: "",
                street2: "", city: "", zip: "", country: "",
                gstin: "", notes: "", saving: false, error: "",
            });
        } catch (e) {
            this.state.error = "Error saving contact. Please try again.";
            console.error("[pos_cash_customer]", e);
            this.state.saving = false;
        }
    }

    discard() {
        this.props.close({ confirmed: false, payload: null });
    }

    async _savePartner() {
        const vals = {
            name: this.state.name.trim(),
            customer_rank: 1,
            type: this.state.contactType || "contact",
        };
        if (this.state.email)   vals.email   = this.state.email.trim();
        if (this.state.phone)   vals.phone   = this.state.phone.trim();
        if (this.state.street)  vals.street  = this.state.street.trim();
        if (this.state.street2) vals.street2 = this.state.street2.trim();
        if (this.state.city)    vals.city    = this.state.city.trim();
        if (this.state.zip)     vals.zip     = this.state.zip.trim();
        if (this.state.notes)   vals.comment = this.state.notes.trim();

        const result = await this.orm.call(
            "res.partner", "create_from_pos_simplified", [vals]
        );

        if (result && result.id) {
            // Load into POS cache using the correct Odoo 19 method
            try {
                const newPartners = await this.orm.read(
                    "res.partner",
                    [result.id],
                    Object.keys(this.pos.models["res.partner"].fields || {})
                );
                if (newPartners && newPartners.length) {
                    this.pos.models["res.partner"].insert(newPartners);
                    return this.pos.models["res.partner"].find(
                        (p) => p.id === result.id
                    );
                }
            } catch (e) {
                console.warn("[pos_cash_customer] Could not insert into POS cache:", e);
            }
            // Fallback: return minimal partner object
            return { id: result.id, name: result.name };
        }
        return null;
    }
}
