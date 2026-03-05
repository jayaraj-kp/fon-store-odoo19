/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class InvoiceListScreen extends Component {
    static template = "pos_invoice_menu.InvoiceListScreen";
    static storeOnOrder = false;

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.state = useState({
            orders: [],
            loading: true,
            searchQuery: "",
            selectedOrder: null,
            errorMessage: "",
        });
        onMounted(() => this.loadOrders());
    }

    async loadOrders() {
        this.state.loading = true;
        this.state.errorMessage = "";
        try {
            const sessionId = this.pos.session.id;
            const orders = await this.orm.call(
                "pos.order",
                "get_pos_orders_for_session",
                [sessionId]
            );
            this.state.orders = orders;
        } catch (error) {
            this.state.errorMessage = "Failed to load orders. Please try again.";
            console.error("POS Invoice Menu error:", error);
        } finally {
            this.state.loading = false;
        }
    }

    get filteredOrders() {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) return this.state.orders;
        return this.state.orders.filter(
            (o) =>
                o.name.toLowerCase().includes(query) ||
                o.partner_name.toLowerCase().includes(query)
        );
    }

    get totalAmount() {
        return this.filteredOrders.reduce((sum, o) => sum + o.amount_total, 0);
    }

    formatCurrency(amount) {
        const symbol = this.pos.currency?.symbol || "";
        return `${symbol} ${parseFloat(amount).toFixed(2)}`;
    }

    formatDate(dateStr) {
        try { return new Date(dateStr).toLocaleString(); }
        catch { return dateStr; }
    }

    getStateBadgeClass(state) {
        return { paid: "badge-success", done: "badge-primary", invoiced: "badge-info" }[state] || "badge-secondary";
    }

    selectOrder(order) {
        this.state.selectedOrder = this.state.selectedOrder?.id === order.id ? null : order;
    }

    isSelected(order) {
        return this.state.selectedOrder?.id === order.id;
    }

    goBack() {
        this.pos.showScreen("ProductScreen");
    }
}

registry.category("pos_screens").add("InvoiceListScreen", InvoiceListScreen);
