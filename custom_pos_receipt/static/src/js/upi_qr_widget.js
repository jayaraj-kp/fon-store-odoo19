/** @odoo-module **/

import { Component, onMounted, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * UpiQrCode – renders a UPI payment QR on a <canvas> element.
 * Uses Odoo's bundled `qr-creator` library (available in Odoo 16+).
 *
 * Props:
 *   upiString  {String}  Full UPI deep-link, e.g.
 *              "upi://pay?pa=xxx@yyy&pn=StoreName&am=100.00&cu=INR"
 *   upiId      {String}  Display-only UPI ID shown below the QR.
 */
export class UpiQrCode extends Component {
    static template = "custom_pos_receipt.UpiQrCode";

    static props = {
        upiString: { type: String },
        upiId:     { type: String },
    };

    setup() {
        this.canvasRef = useRef("upiCanvas");
        onMounted(() => this._renderQr());
    }

    async _renderQr() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;

        try {
            // qr-creator is bundled with Odoo web assets
            const QRCreator = (await odoo.loader.modules.get("qr-creator"))?.default
                           || (await import("qr-creator")).default;

            QRCreator.render(
                {
                    text:         this.props.upiString,
                    radius:       0.0,
                    ecLevel:      "M",
                    fill:         "#000000",
                    background:   "#ffffff",
                    size:         120,
                },
                canvas
            );
        } catch (e) {
            // Graceful fallback: draw a placeholder if library fails to load
            console.warn("[UpiQrCode] qr-creator not available:", e);
            const ctx = canvas.getContext("2d");
            canvas.width  = 120;
            canvas.height = 120;
            ctx.strokeStyle = "#000";
            ctx.lineWidth   = 2;
            ctx.strokeRect(4, 4, 112, 112);
            ctx.font        = "9px monospace";
            ctx.fillStyle   = "#000";
            ctx.textAlign   = "center";
            ctx.fillText("Scan UPI", 60, 60);
            ctx.fillText(this.props.upiId, 60, 76);
        }
    }
}

// Register so the XML template can reference it
registry.category("pos_receipt_components").add("UpiQrCode", UpiQrCode);