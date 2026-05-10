/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, useRef } from "@odoo/owl";

/**
 * BarcodeLabelPrintDialog
 *
 * Identical split-screen layout to the invoice print dialog.
 * The key difference: pdfPreviewUrl comes directly from params.pdf_url
 * (our custom controller /custom_barcode_label/report/pdf/<ids>?qty=<n>)
 * instead of being constructed as /report/pdf/<report>/<id>.
 *
 * This bypasses the standard Odoo report route which doesn't support
 * passing label_qty via GET parameters.
 */
export class BarcodeLabelPrintDialog extends Component {
    static template = "custom_barcode_label.BarcodeLabelPrintDialog";
    static components = { Dialog };
    static props = {
        pdfUrl:       { type: String },
        recordName:   { type: String, optional: true },
        docLabel:     { type: String, optional: true },
        labelQty:     { type: Number, optional: true },
        productCount: { type: Number, optional: true },
        close:        { type: Function },
    };

    setup() {
        this.notification    = useService("notification");
        this.iframeRef       = useRef("previewIframe");

        // Use our custom controller URL directly
        this.pdfPreviewUrl  = this.props.pdfUrl;
        this.pdfDownloadUrl = this.props.pdfUrl +
            (this.props.pdfUrl.includes('?') ? '&' : '?') + 'download=true';

        this.state = useState({
            loading:   true,
            loadError: false,
            format:    "pdf",
            savePath:  "",
            fileHandle: null,
            saving:    false,
        });
    }

    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
    onIframeError() { this.state.loading = false; this.state.loadError = true; }

    async onChooseLocation() {
        const name = `${this.props.recordName || "barcode_labels"}.pdf`;
        if (window.showSaveFilePicker) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: name,
                    types: [{ description: "PDF Document", accept: { "application/pdf": [".pdf"] } }],
                });
                this.state.fileHandle = handle;
                this.state.savePath   = handle.name;
            } catch (err) {
                if (err.name !== "AbortError") console.warn("File picker error:", err);
            }
        } else {
            this.state.savePath = name;
            this.notification.add("Will save to Downloads folder.", { type: "info" });
        }
    }

    async onSave() {
        const fileName = `${this.props.recordName || "barcode_labels"}.pdf`;
        this.state.saving = true;
        try {
            const blob = await this._xhrBlob(this.pdfDownloadUrl);
            await this._writeBlob(blob, fileName);
        } catch (err) {
            console.error("Save failed:", err);
            this.notification.add(`Save failed: ${err.message}`, { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    _xhrBlob(url) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open("GET", url, true);
            xhr.responseType    = "blob";
            xhr.withCredentials = true;
            xhr.onload  = () => xhr.status < 300
                ? resolve(xhr.response)
                : reject(new Error(`Server returned ${xhr.status}`));
            xhr.onerror = () => reject(new Error("Network error"));
            xhr.send();
        });
    }

    async _writeBlob(blob, fileName) {
        if (this.state.fileHandle) {
            try {
                const writable = await this.state.fileHandle.createWritable();
                await writable.write(blob);
                await writable.close();
                this.notification.add(`Saved: ${this.state.fileHandle.name}`, { type: "success" });
                return;
            } catch (err) {
                console.warn("createWritable failed, using download:", err);
            }
        }
        const blobUrl = URL.createObjectURL(blob);
        const link    = document.createElement("a");
        link.href     = blobUrl;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
        this.notification.add("PDF download started", { type: "success" });
    }

    onPrint() {
        const win = window.open(this.pdfPreviewUrl, "_blank");
        if (!win) {
            this.notification.add("Pop-up blocked. Please allow pop-ups.", { type: "warning" });
            return;
        }
        win.onload = () => setTimeout(() => { win.focus(); win.print(); }, 600);
    }

    onClose() { this.props.close(); }

    get dialogTitle() {
        const label = this.props.docLabel || "Barcode Label";
        const name  = this.props.recordName || "";
        return `Print — ${label}${name ? ": " + name : ""}`;
    }

    get saveButtonLabel()  { return this.state.saving ? "Saving..." : "Save as PDF"; }
    get saveButtonIcon()   { return this.state.saving ? "fa fa-spinner fa-spin" : "fa fa-file-pdf-o"; }
    get locationPlaceholder() { return `${this.props.recordName || "barcode_labels"}.pdf`; }
}

// Register under our own tag so it doesn't conflict with custom_print_dialog
registry.category("actions").add(
    "custom_barcode_label.open_print_dialog",
    async (env, action) => {
        const p = action.params || {};
        env.services.dialog.add(BarcodeLabelPrintDialog, {
            pdfUrl:       p.pdf_url,
            recordName:   p.record_name,
            docLabel:     p.doc_label || "Barcode Label",
            labelQty:     p.label_qty || 1,
            productCount: p.product_count || 1,
        });
    }
);
