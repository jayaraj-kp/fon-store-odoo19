/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

/**
 * Simplified "Create Contact" popup for POS.
 * Mirrors the sub-contact wizard (Image 2) with:
 * - Contact type tabs: Contact / Invoice / Delivery / Other
 * - Name, Email, Phone
 * - Address fields
 * - GSTIN, Tags
 * - Internal Notes
 * - Save & Close / Save & New / Discard buttons
 */
export class CreateContactPopup extends AbstractAwaitablePopup {
    static template = "pos_cash_customer.CreateContactPopup";
    static defaultProps = {
        confirmText: "Save & Close",
        cancelText: "Discard",
        title: "Create Contact",
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            contactType: "contact",  // contact | invoice | delivery | other
            name: "",
            email: "",
            phone: "",
            street: "",
            street2: "",
            city: "",
            zip: "",
            state_name: "",
            country: "",
            gstin: "",
            tags: "",
            notes: "",
            saving: false,
            error: "",
        });
    }

    setContactType(type) {
        this.state.contactType = type;
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
            this.confirm(partner);
        } catch (e) {
            this.state.error = "Error saving contact. Please try again.";
            console.error(e);
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
            // Reset form for new entry
            Object.assign(this.state, {
                name: "",
                email: "",
                phone: "",
                street: "",
                street2: "",
                city: "",
                zip: "",
                state_name: "",
                country: "",
                gstin: "",
                tags: "",
                notes: "",
                saving: false,
                error: "",
            });
        } catch (e) {
            this.state.error = "Error saving contact. Please try again.";
            console.error(e);
        } finally {
            this.state.saving = false;
        }
    }

    async _savePartner() {
        const vals = {
            name: this.state.name.trim(),
            customer_rank: 1,
        };
        if (this.state.email) vals.email = this.state.email.trim();
        if (this.state.phone) vals.phone = this.state.phone.trim();
        if (this.state.street) vals.street = this.state.street.trim();
        if (this.state.street2) vals.street2 = this.state.street2.trim();
        if (this.state.city) vals.city = this.state.city.trim();
        if (this.state.zip) vals.zip = this.state.zip.trim();
        if (this.state.notes) vals.comment = this.state.notes.trim();

        // Map contact type to Odoo type field
        const typeMap = {
            contact: "contact",
            invoice: "invoice",
            delivery: "delivery",
            other: "other",
        };
        vals.type = typeMap[this.state.contactType] || "contact";

        // Call server to create partner
        const result = await this.orm.call(
            "res.partner",
            "create_from_pos_simplified",
            [vals]
        );

        // Load the new partner into POS cache
        if (result && result.id) {
            const newPartners = await this.orm.read(
                "res.partner",
                [result.id],
                this.pos.models["res.partner"].fields
            );
            if (newPartners && newPartners.length) {
                this.pos.models["res.partner"].insert(newPartners);
                return this.pos.models["res.partner"].find(
                    (p) => p.id === result.id
                );
            }
        }
        return null;
    }

    getButtonLabel(type) {
        const labels = {
            contact: "Contact",
            invoice: "Invoice",
            delivery: "Delivery",
            other: "Other",
        };
        return labels[type] || type;
    }
}
