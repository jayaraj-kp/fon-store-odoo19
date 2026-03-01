/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SpecialOfferPopup extends Component {
    static template = "pos_special_offers.SpecialOfferPopup";

    static props = {
        products: Array,
        categories: Array,
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.specialOfferService = useService("special_offer_service");

        this.state = useState({
            offerName: "",
            selectedProducts: [],
            selectedCategory: null,
            dateFrom: this._today(),
            dateTo: this._today(),
            activeTime: "00:00",
            discountType: "percentage",
            discountValue: "10",
            loading: false,
            showSuccess: false,
            lastCreatedName: "",
            errorMsg: "",
        });
    }

    _today() {
        return new Date().toISOString().split("T")[0];
    }

    onOverlayClick() {
        // close when clicking outside
        this.props.close();
    }

    onClose() {
        this.props.close();
    }

    onOfferNameInput(ev) {
        this.state.offerName = ev.target.value;
    }

    onProductChange(ev) {
        this.state.selectedProducts = [...ev.target.selectedOptions].map(o => parseInt(o.value));
    }

    onCategoryChange(ev) {
        this.state.selectedCategory = ev.target.value ? parseInt(ev.target.value) : null;
    }

    onDateFromInput(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToInput(ev) {
        this.state.dateTo = ev.target.value;
    }

    onTimeInput(ev) {
        this.state.activeTime = ev.target.value;
    }

    onDiscountTypeChange(ev) {
        this.state.discountType = ev.target.value;
    }

    onDiscountValueInput(ev) {
        this.state.discountValue = ev.target.value;
    }

    async onCreateOffer() {
        this.state.errorMsg = "";
        this.state.showSuccess = false;

        // Validation
        if (!this.state.offerName.trim()) {
            this.state.errorMsg = "Please enter an Offer Name.";
            return;
        }
        if (!this.state.dateFrom || !this.state.dateTo) {
            this.state.errorMsg = "Please select both From Date and To Date.";
            return;
        }
        if (this.state.dateFrom > this.state.dateTo) {
            this.state.errorMsg = "From Date cannot be after To Date.";
            return;
        }
        if (!this.state.discountValue || parseFloat(this.state.discountValue) <= 0) {
            this.state.errorMsg = "Please enter a valid Discount Value.";
            return;
        }
        if (this.state.selectedProducts.length === 0 && !this.state.selectedCategory) {
            this.state.errorMsg = "Please select at least one Product or Category.";
            return;
        }

        // Convert time "HH:MM" → float
        const [hours, minutes] = this.state.activeTime.split(":").map(Number);
        const timeFloat = hours + (minutes || 0) / 60.0;

        this.state.loading = true;
        try {
            await this.orm.create("pos.special.offer", [{
                name: this.state.offerName.trim(),
                product_ids: [[6, 0, this.state.selectedProducts]],
                category_ids: this.state.selectedCategory
                    ? [[6, 0, [this.state.selectedCategory]]]
                    : [[6, 0, []]],
                date_from: this.state.dateFrom,
                date_to: this.state.dateTo,
                active_time: timeFloat,
                discount_type: this.state.discountType,
                discount_value: parseFloat(this.state.discountValue),
                active: true,
            }]);

            // Refresh the service cache
            await this.specialOfferService.refresh();

            this.state.lastCreatedName = this.state.offerName;
            this.state.showSuccess = true;

            // Reset form
            this.state.offerName = "";
            this.state.selectedProducts = [];
            this.state.selectedCategory = null;
            this.state.dateFrom = this._today();
            this.state.dateTo = this._today();
            this.state.activeTime = "00:00";
            this.state.discountValue = "10";

        } catch (err) {
            this.state.errorMsg = "Failed to create offer. Please check your inputs and try again.";
            console.error("[SpecialOffer] Error creating offer:", err);
        } finally {
            this.state.loading = false;
        }
    }
}
