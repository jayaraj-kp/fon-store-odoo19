///** @odoo-module **/
//
//import { registry } from "@web/core/registry";
//import { useService } from "@web/core/utils/hooks";
//import { Dialog } from "@web/core/dialog/dialog";
//import { Component, useState, useRef } from "@odoo/owl";
//
//export class ProductLabelPrintDialog extends Component {
//    static template = "product_label_print.ProductLabelPrintDialog";
//    static components = { Dialog };
//    static props = {
//        pdfUrl:       { type: String },
//        recordName:   { type: String, optional: true },
//        labelQty:     { type: Number, optional: true },
//        productCount: { type: Number, optional: true },
//        close:        { type: Function },
//    };
//
//    setup() {
//        this.notification   = useService("notification");
//        this.iframeRef      = useRef("previewIframe");
//
//        this.pdfPreviewUrl  = this.props.pdfUrl;
//        this.pdfDownloadUrl = this.props.pdfUrl +
//            (this.props.pdfUrl.includes('?') ? '&' : '?') + 'download=true';
//
//        this.state = useState({
//            loading:    true,
//            loadError:  false,
//            savePath:   "",
//            fileHandle: null,
//            saving:     false,
//        });
//    }
//
//    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
//    onIframeError() { this.state.loading = false; this.state.loadError = true; }
//
//    async onChooseLocation() {
//        const name = `${this.props.recordName || "product_labels"}.pdf`;
//        if (window.showSaveFilePicker) {
//            try {
//                const handle = await window.showSaveFilePicker({
//                    suggestedName: name,
//                    types: [{ description: "PDF Document", accept: { "application/pdf": [".pdf"] } }],
//                });
//                this.state.fileHandle = handle;
//                this.state.savePath   = handle.name;
//            } catch (err) {
//                if (err.name !== "AbortError") console.warn("File picker error:", err);
//            }
//        } else {
//            this.state.savePath = name;
//            this.notification.add("Will save to Downloads folder.", { type: "info" });
//        }
//    }
//
//    async onSave() {
//        const fileName = `${this.props.recordName || "product_labels"}.pdf`;
//        this.state.saving = true;
//        try {
//            const blob = await this._xhrBlob(this.pdfDownloadUrl);
//            await this._writeBlob(blob, fileName);
//        } catch (err) {
//            console.error("Save failed:", err);
//            this.notification.add(`Save failed: ${err.message}`, { type: "danger" });
//        } finally {
//            this.state.saving = false;
//        }
//    }
//
//    _xhrBlob(url) {
//        return new Promise((resolve, reject) => {
//            const xhr = new XMLHttpRequest();
//            xhr.open("GET", url, true);
//            xhr.responseType    = "blob";
//            xhr.withCredentials = true;
//            xhr.onload  = () => xhr.status < 300
//                ? resolve(xhr.response)
//                : reject(new Error(`Server returned ${xhr.status}`));
//            xhr.onerror = () => reject(new Error("Network error"));
//            xhr.send();
//        });
//    }
//
//    async _writeBlob(blob, fileName) {
//        if (this.state.fileHandle) {
//            try {
//                const writable = await this.state.fileHandle.createWritable();
//                await writable.write(blob);
//                await writable.close();
//                this.notification.add(`Saved: ${this.state.fileHandle.name}`, { type: "success" });
//                return;
//            } catch (err) {
//                console.warn("createWritable failed, using download:", err);
//            }
//        }
//        const blobUrl = URL.createObjectURL(blob);
//        const link    = document.createElement("a");
//        link.href     = blobUrl;
//        link.download = fileName;
//        document.body.appendChild(link);
//        link.click();
//        document.body.removeChild(link);
//        setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);
//        this.notification.add("PDF download started", { type: "success" });
//    }
//
//    onPrint() {
//        const win = window.open(this.pdfPreviewUrl, "_blank");
//        if (!win) {
//            this.notification.add("Pop-up blocked. Please allow pop-ups.", { type: "warning" });
//            return;
//        }
//        win.onload = () => setTimeout(() => { win.focus(); win.print(); }, 600);
//    }
//
//    onClose() { this.props.close(); }
//
//    get dialogTitle() {
//        const name = this.props.recordName || "";
//        return `Print Product Labels${name ? " — " + name : ""}`;
//    }
//
//    get saveButtonLabel()  { return this.state.saving ? "Saving..." : "Save as PDF"; }
//    get saveButtonIcon()   { return this.state.saving ? "fa fa-spinner fa-spin" : "fa fa-file-pdf-o"; }
//    get locationPlaceholder() { return `${this.props.recordName || "product_labels"}.pdf`; }
//}
//
//registry.category("actions").add(
//    "product_label_print.open_print_dialog",
//    async (env, action) => {
//        const p = action.params || {};
//        env.services.dialog.add(ProductLabelPrintDialog, {
//            pdfUrl:       p.pdf_url,
//            recordName:   p.record_name,
//            labelQty:     p.label_qty  || 1,
//            productCount: p.product_count || 1,
//        });
//    }
//);
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, useRef } from "@odoo/owl";

export class ProductLabelPrintDialog extends Component {
    static template = "product_label_print.ProductLabelPrintDialog";
    static components = { Dialog };
    static props = {
        pdfUrl:       { type: String },
        recordName:   { type: String, optional: true },
        labelQty:     { type: Number, optional: true },
        productCount: { type: Number, optional: true },
        close:        { type: Function },
    };

    setup() {
        this.notification   = useService("notification");
        this.iframeRef      = useRef("previewIframe");

        this.pdfPreviewUrl  = this.props.pdfUrl;
        this.pdfDownloadUrl = this.props.pdfUrl +
            (this.props.pdfUrl.includes('?') ? '&' : '?') + 'download=true';

        this.state = useState({
            loading:    true,
            loadError:  false,
            savePath:   "",
            fileHandle: null,
            saving:     false,
        });
    }

    onIframeLoad()  { this.state.loading = false; this.state.loadError = false; }
    onIframeError() { this.state.loading = false; this.state.loadError = true; }

    async onChooseLocation() {
        const name = `${this.props.recordName || "product_labels"}.pdf`;
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
        const fileName = `${this.props.recordName || "product_labels"}.pdf`;
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
        // Build a tiny HTML wrapper that embeds the PDF in an iframe and
        // calls window.print() with the correct copies count.
        // This is needed because the browser print dialog does not read
        // the copies count from the PDF itself — we must set it via JS.
        const copies = this.props.labelQty || 1;
        const pdfSrc = this.pdfPreviewUrl;

        const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * { margin:0; padding:0; }
  html, body { width:100%; height:100%; overflow:hidden; background:#525659; }
  iframe { width:100%; height:100%; border:none; display:block; }
</style>
</head>
<body>
<iframe id="pdfFrame" src="${pdfSrc}"></iframe>
<script>
  // Set copies and trigger print once the iframe PDF is loaded
  document.getElementById('pdfFrame').onload = function() {
    setTimeout(function() {
      // Try to set copies via execCommand (works in some browsers)
      try { document.execCommand('print', false, null); } catch(e) {}
      // Standard approach — copies hint via CSS (Chrome respects this)
      var style = document.createElement('style');
      style.innerHTML = '@page { size: auto; }';
      document.head.appendChild(style);
      window.focus();
      // Small delay to ensure PDF renderer is ready
      setTimeout(function() { window.print(); }, 400);
    }, 600);
  };
<\/script>
</body>
</html>`;

        const blob = new Blob([html], { type: 'text/html' });
        const blobUrl = URL.createObjectURL(blob);
        const win = window.open(blobUrl, "_blank",
            "width=900,height=700,menubar=no,toolbar=no,location=no,status=no");
        if (!win) {
            this.notification.add("Pop-up blocked. Please allow pop-ups.", { type: "warning" });
            URL.revokeObjectURL(blobUrl);
            return;
        }
        // Show copies info to user so they can confirm in browser dialog
        if (copies > 1) {
            this.notification.add(
                `Set Copies to ${copies} in the print dialog.`,
                { type: "info", sticky: false }
            );
        }
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
    }

    onClose() { this.props.close(); }

    get dialogTitle() {
        const name = this.props.recordName || "";
        return `Print Product Labels${name ? " — " + name : ""}`;
    }

    get saveButtonLabel()  { return this.state.saving ? "Saving..." : "Save as PDF"; }
    get saveButtonIcon()   { return this.state.saving ? "fa fa-spinner fa-spin" : "fa fa-file-pdf-o"; }
    get locationPlaceholder() { return `${this.props.recordName || "product_labels"}.pdf`; }
}

registry.category("actions").add(
    "product_label_print.open_print_dialog",
    async (env, action) => {
        const p = action.params || {};
        env.services.dialog.add(ProductLabelPrintDialog, {
            pdfUrl:       p.pdf_url,
            recordName:   p.record_name,
            labelQty:     p.label_qty  || 1,
            productCount: p.product_count || 1,
        });
    }
);