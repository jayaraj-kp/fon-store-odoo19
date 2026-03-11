/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

const CASH_CUSTOMER_NAME = "CASH CUSTOMER";
const MIN_CHARS = 3; // dropdown appears after this many characters

export class PhoneCustomerBar extends Component {
    static template = "pos_cash_customer_contact.PhoneCustomerBar";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.inputRef = useRef("input");
        this.state = useState({
            query: "",
            suggestions: [],
            showDropdown: false,
            selectedName: "",
            found: false,
            creating: false,
        });
    }

    _getSuggestions(query) {
        if (!query || query.length < MIN_CHARS) return [];
        const q = query.toLowerCase();
        return this.pos.models["res.partner"]
            .filter((p) => {
                if (!p.name) return false;
                const matchName = p.name.toLowerCase().includes(q);
                const matchPhone = (p.phone || "").includes(q);
                const matchMobile = (p.mobile || "").includes(q);
                return matchName || matchPhone || matchMobile;
            })
            .slice(0, 8); // max 8 suggestions
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
        this.state.showDropdown = suggestions.length > 0;

        // If exact match on phone/mobile → auto-assign silently
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
        this.state.creating = false;
        this.state.suggestions = [];
        this.state.showDropdown = false;
        this.pos.getOrder().setPartner(false);
    }

    onBlur() {
        // Delay so click on suggestion fires first
        setTimeout(() => {
            this.state.showDropdown = false;
        }, 200);
    }

    onFocus() {
        if (this.state.suggestions.length > 0) {
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

    async onCreateCustomer() {
        if (!this.state.query || this.state.creating) return;
        this.state.creating = true;

        try {
            const parentId = await this._getCashCustomerParentId();

            const rawId = await this.orm.create("res.partner", [{
                name: this.state.query,
                phone: this.state.query,
                parent_id: parentId,
                customer_rank: 1,
            }]);
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
                this.state.found = true;
                this.state.selectedName = newPartner.name;
                this.state.showDropdown = false;
                this.notification.add(
                    `Customer created under ${CASH_CUSTOMER_NAME}`,
                    { type: "success", sticky: false }
                );
            } else {
                throw new Error("Partner not found in cache after load");
            }
        } catch (err) {
            console.error("Failed to create customer:", err);
            this.notification.add(
                "Could not create customer: " + (err.message || err),
                { type: "danger", sticky: false }
            );
        } finally {
            this.state.creating = false;
        }
    }
}

patch(ProductScreen, {
    components: {
        ...ProductScreen.components,
        PhoneCustomerBar,
    },
});