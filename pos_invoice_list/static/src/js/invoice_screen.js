/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class InvoiceScreen extends Component {
    static template = "pos_invoice_list.InvoiceScreen";
    static storeOnOrder = false;
    static props = {};

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            invoices: [],
            loading: true,
            searchTerm: "",
        });

        onWillStart(async () => {
            await this.loadInvoices();
        });
    }

    async loadInvoices() {
        this.state.loading = true;
        try {
            // Fetch invoices linked to POS orders only
            // account.move where move_type = 'out_invoice' and pos_order_ids is set
            const invoices = await this.orm.searchRead(
                "account.move",
                [
                    ["move_type", "=", "out_invoice"],
                    ["pos_order_ids", "!=", false],
                ],
                ["name", "partner_id", "invoice_date", "amount_total", "payment_state", "id"],
                { order: "invoice_date desc", limit: 100 }
            );
            this.state.invoices = invoices;
        } catch (e) {
            this.notification.add(_t("Failed to load invoices."), { type: "danger" });
            this.state.invoices = [];
        }
        this.state.loading = false;
    }

    get filteredInvoices() {
        const term = this.state.searchTerm.toLowerCase().trim();
        if (!term) return this.state.invoices;
        return this.state.invoices.filter((inv) => {
            const partner = (inv.partner_id?.[1] || "").toLowerCase();
            const name = (inv.name || "").toLowerCase();
            return name.includes(term) || partner.includes(term);
        });
    }

    getPaymentBadge(paymentState) {
        const map = {
            paid: { label: "Paid", cls: "text-bg-success" },
            not_paid: { label: "Unpaid", cls: "text-bg-danger" },
            in_payment: { label: "In Payment", cls: "text-bg-warning" },
            partial: { label: "Partial", cls: "text-bg-warning" },
            reversed: { label: "Reversed", cls: "text-bg-secondary" },
        };
        return map[paymentState] || { label: paymentState, cls: "text-bg-secondary" };
    }

    formatAmount(amount) {
        return this.env.utils.formatCurrency(amount);
    }

    formatDate(dateStr) {
        if (!dateStr) return "—";
        // dateStr is like "2026-03-14"
        const [y, m, d] = dateStr.split("-");
        return `${d}/${m}/${y}`;
    }

    async onClickInvoice(invoice) {
        // Open the invoice in backend using action
        try {
            const action = await this.orm.call(
                "account.move",
                "get_formview_action",
                [[invoice.id]]
            );
            // Navigate to backend
            window.open(`/odoo/accounting/customer-invoices/${invoice.id}`, "_blank");
        } catch (e) {
            // Fallback: open directly
            window.open(`/odoo/accounting/customer-invoices/${invoice.id}`, "_blank");
        }
    }

    onClickBack() {
        this.pos.navigate("ProductScreen");
    }

    onSearch(ev) {
        this.state.searchTerm = ev.target.value;
    }
}

registry.category("pos_pages").add("InvoiceScreen", {
    name: "InvoiceScreen",
    component: InvoiceScreen,
    route: `/pos/ui/${odoo.pos_config_id}/invoices`,
    params: {},
});
