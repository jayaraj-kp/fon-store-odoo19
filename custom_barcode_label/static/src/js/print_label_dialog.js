/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * PrintLabelDialog
 * ─────────────────
 * Opens the PDF in a hidden <iframe>, then calls iframe.contentWindow.print()
 * so the OS/browser print dialog appears — exactly the same way the POS
 * receipt print works.  The user can then pick any installed printer.
 */
class PrintLabelDialog extends Component {
    static template = "custom_barcode_label.PrintLabelDialog";
    static components = { Dialog };
    static props = {
        pdf_url: String,
        label_qty: Number,
        product_count: Number,
        close: Function,
    };

    setup() {
        this.iframeRef = useRef("printIframe");
        this.state = useState({ status: "loading", error: null });

        onMounted(() => {
            this._loadAndPrint();
        });
    }

    async _loadAndPrint() {
        const iframe = this.iframeRef.el;
        if (!iframe) return;

        iframe.onload = () => {
            this.state.status = "ready";
            // Small delay so the PDF renders fully before the print dialog
            setTimeout(() => {
                try {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (e) {
                    // Cross-origin fallback: open in new tab for printing
                    window.open(this.props.pdf_url, "_blank");
                }
            }, 800);
        };

        iframe.onerror = () => {
            this.state.status = "error";
            this.state.error = "Could not load the PDF. Please use Download PDF instead.";
        };

        iframe.src = this.props.pdf_url;
    }

    onDownload() {
        window.open(this.props.pdf_url, "_blank");
    }

    onClose() {
        this.props.close();
    }
}

/**
 * Client action handler registered as "custom_barcode_label.print_dialog"
 * The Python wizard returns this action tag with params.
 */
const printLabelClientAction = {
    Component: class extends Component {
        static template = "custom_barcode_label.PrintLabelClientAction";
        static components = { PrintLabelDialog };

        setup() {
            this.dialog = useService("dialog");
            this.action = useService("action");

            onMounted(() => {
                const params = this.props.action.params || {};
                this.dialog.add(PrintLabelDialog, {
                    pdf_url: params.pdf_url,
                    label_qty: params.label_qty || 1,
                    product_count: params.product_count || 1,
                });
                // Go back after dialog is added
                this.action.restore();
            });
        }
    },
};

registry.category("actions").add(
    "custom_barcode_label.print_dialog",
    printLabelClientAction.Component
);
