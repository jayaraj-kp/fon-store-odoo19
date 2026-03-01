/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ─────────────────────────────────────────────
// Special Offers Screen Component
// ─────────────────────────────────────────────
class SpecialOffersScreen extends Component {
    static template = "pos_special_offers.SpecialOffersScreen";
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            programs: [],
            loading: true,
            selectedProgram: null,
            showCreateForm: false,
            newProgram: {
                name: "",
                program_type: "coupons",
                trigger: "with_code",
            },
            generatingCoupon: false,
            generatedCode: null,
        });

        onMounted(() => this.loadPrograms());
    }

    async loadPrograms() {
        try {
            const programs = await this.orm.searchRead(
                "loyalty.program",
                [
                    ["pos_config_ids", "in", [this.pos.config.id]],
                    ["active", "=", true],
                ],
                ["id", "name", "program_type", "trigger", "reward_ids", "coupon_ids"],
                { limit: 100 }
            );
            this.state.programs = programs;
        } catch (e) {
            console.error("Failed to load programs:", e);
        } finally {
            this.state.loading = false;
        }
    }

    selectProgram(program) {
        this.state.selectedProgram =
            this.state.selectedProgram?.id === program.id ? null : program;
        this.state.generatedCode = null;
    }

    async generateCoupon() {
        if (!this.state.selectedProgram) return;
        this.state.generatingCoupon = true;
        try {
            const result = await this.orm.call(
                "loyalty.program",
                "generate_coupons",
                [[this.state.selectedProgram.id]],
                { count: 1 }
            );
            // Fetch the generated coupon code
            const coupons = await this.orm.searchRead(
                "loyalty.card",
                [["program_id", "=", this.state.selectedProgram.id]],
                ["code", "expiration_date", "points"],
                { limit: 1, order: "id desc" }
            );
            this.state.generatedCode = coupons[0]?.code || "Generated!";
            this.notification.add(`Coupon generated: ${this.state.generatedCode}`, {
                type: "success",
                title: "Coupon Created",
            });
        } catch (e) {
            this.notification.add("Failed to generate coupon. Check program settings.", {
                type: "danger",
                title: "Error",
            });
        } finally {
            this.state.generatingCoupon = false;
        }
    }

    copyCode() {
        if (this.state.generatedCode) {
            navigator.clipboard.writeText(this.state.generatedCode);
            this.notification.add("Coupon code copied!", { type: "info" });
        }
    }

    openBackendProgram(programId) {
        // Open the backend form in a new tab
        const url = `/web#model=loyalty.program&id=${programId}&view_type=form`;
        window.open(url, "_blank");
    }

    getProgramTypeLabel(type) {
        const labels = {
            coupons: "Coupons",
            gift_card: "Gift Card",
            loyalty: "Loyalty Card",
            promotion: "Promotions",
            ewallet: "eWallet",
            buy_x_get_y: "Buy X Get Y",
            next_order_coupons: "Next Order Coupon",
        };
        return labels[type] || type;
    }

    getProgramTypeIcon(type) {
        const icons = {
            coupons: "🎟️",
            gift_card: "🎁",
            loyalty: "⭐",
            promotion: "🏷️",
            ewallet: "💳",
            buy_x_get_y: "🛒",
            next_order_coupons: "🔄",
        };
        return icons[type] || "📋";
    }

    get activePrograms() {
        return this.state.programs.filter(
            (p) => p.program_type === "coupons" || p.program_type === "promotion"
        );
    }

    get loyaltyPrograms() {
        return this.state.programs.filter(
            (p) => p.program_type === "loyalty" || p.program_type === "gift_card"
        );
    }

    closeScreen() {
        this.pos.showScreen("ProductScreen");
    }
}

// ─────────────────────────────────────────────
// Special Offers Button (top menu)
// ─────────────────────────────────────────────
class SpecialOffersButton extends Component {
    static template = "pos_special_offers.SpecialOffersButton";
    static props = {};

    setup() {
        this.pos = usePos();
    }

    get showButton() {
        return this.pos.config.show_special_offers_button !== false;
    }

    openSpecialOffers() {
        this.pos.showScreen("SpecialOffersScreen");
    }
}

// Register the screen
registry.category("pos_screens").add("SpecialOffersScreen", SpecialOffersScreen);

// Register the button in the header
registry.category("pos_header_buttons").add("SpecialOffersButton", {
    component: SpecialOffersButton,
    condition: (pos) => pos.config.show_special_offers_button !== false,
});

export { SpecialOffersScreen, SpecialOffersButton };
