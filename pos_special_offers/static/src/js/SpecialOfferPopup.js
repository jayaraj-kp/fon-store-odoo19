/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * SpecialOfferPopup
 * Modal dialog shown when the cashier clicks "Offers" in the POS top bar.
 * - "Create Offer" tab: form to create a new pos.special.offer record
 * - "Active Offers" tab: lists currently running offers
 */
export class SpecialOfferPopup extends Component {
    static template = "pos_special_offers.SpecialOfferPopup";

    static props = {
        products: { type: Array },
        categories: { type: Array },
        close: { type: Function },
    };

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            tab: "create",
            // Form fields
            offerName: "",
            selectedProducts: [],
            selectedCategory: "",
            dateFrom: this._today(),
            dateTo: this._today(),
            timeFrom: "00:00",
            timeTo: "23:59",
            discountType: "percentage",
            discountValue: 10,
            // Feedback
            successMsg: "",
            activeOffers: [],
        });

        onWillStart(async () => {
            await this.loadActiveOffers();
        });
    }

    // ─── Helpers ────────────────────────────────────────────────────────────

    _today() {
        return new Date().toISOString().split("T")[0];
    }

    _timeToFloat(timeStr) {
        // "12:30" → 12.5
        const [h, m] = timeStr.split(":").map(Number);
        return h + m / 60.0;
    }

    // ─── Tab ────────────────────────────────────────────────────────────────

    setTab(tab) {
        this.state.tab = tab;
        if (tab === "list") {
            this.loadActiveOffers();
        }
    }

    // ─── Events ─────────────────────────────────────────────────────────────

    onProductSelect(ev) {
        this.state.selectedProducts = [...ev.target.selectedOptions].map((o) =>
            parseInt(o.value)
        );
    }

    onCategorySelect(ev) {
        this.state.selectedCategory = ev.target.value
            ? parseInt(ev.target.value)
            : "";
    }

    onClose() {
        this.props.close();
    }

    // ─── Create Offer ────────────────────────────────────────────────────────

    async createOffer() {
        const { offerName, dateFrom, dateTo, selectedProducts, selectedCategory,
                timeFrom, timeTo, discountType, discountValue } = this.state;

        // Basic validation
        if (!offerName.trim()) {
            alert("Please enter an Offer Name.");
            return;
        }
        if (!dateFrom || !dateTo) {
            alert("Please select From Date and To Date.");
            return;
        }
        if (selectedProducts.length === 0 && !selectedCategory) {
            alert("Please select at least one Product or a Category.");
            return;
        }
        if (dateFrom > dateTo) {
            alert("From Date cannot be later than To Date.");
            return;
        }

        const vals = {
            name: offerName.trim(),
            date_from: dateFrom,
            date_to: dateTo,
            active_time: this._timeToFloat(timeFrom),
            active_time_end: this._timeToFloat(timeTo),
            discount_type: discountType,
            discount_value: parseFloat(discountValue) || 0,
            product_ids: [[6, 0, selectedProducts]],
            category_ids: selectedCategory
                ? [[6, 0, [selectedCategory]]]
                : [[6, 0, []]],
        };

        try {
            await this.orm.create("pos.special.offer", [vals]);
            this.state.successMsg = `Offer "${offerName}" created successfully!`;
            // Reset form
            this.state.offerName = "";
            this.state.selectedProducts = [];
            this.state.selectedCategory = "";
            this.state.dateFrom = this._today();
            this.state.dateTo = this._today();
            this.state.timeFrom = "00:00";
            this.state.timeTo = "23:59";
            this.state.discountType = "percentage";
            this.state.discountValue = 10;
            // Auto-clear success message after 4 seconds
            setTimeout(() => { this.state.successMsg = ""; }, 4000);
        } catch (e) {
            alert("Error creating offer: " + (e.message || e));
        }
    }

    // ─── Load Active Offers ──────────────────────────────────────────────────

    async loadActiveOffers() {
        try {
            const offers = await this.orm.call(
                "pos.special.offer",
                "get_active_offers_for_pos",
                []
            );
            this.state.activeOffers = offers;
        } catch (e) {
            this.state.activeOffers = [];
        }
    }
}
