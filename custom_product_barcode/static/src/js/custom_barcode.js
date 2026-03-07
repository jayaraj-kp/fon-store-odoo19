/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v15 — price fix)
 *
 * FIX: Pass price_unit directly inside addLineToCurrentOrder call.
 * Odoo 19 accepts { product_id, qty, price_unit } in one shot — no
 * separate setPriceOnLine step needed.
 *
 * Price rule:
 *   Package Price > 0  →  unit_price on line = package_price / qty
 *                         so POS shows:  qty × (package_price/qty) = package_price ✅
 *   Package Price = 0  →  use product's default unit price (no override)
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

let _customBarcodeMap = null;
let _fetchPromise     = null;

async function fetchCustomBarcodeMap() {
    if (_customBarcodeMap !== null) return _customBarcodeMap;
    if (_fetchPromise)              return _fetchPromise;
    _fetchPromise = (async () => {
        try {
            const resp = await fetch('/pos/custom_barcode_map', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const json = await resp.json();
            const raw  = (json?.result ?? json)?.barcodes ?? {};
            _customBarcodeMap = {};
            for (const [k, v] of Object.entries(raw))
                _customBarcodeMap[k.toUpperCase()] = v;
            console.log(`[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} package barcode(s) loaded.`);
        } catch (e) {
            console.error('[CustomBarcode] Failed to load barcode map:', e);
            _customBarcodeMap = {};
        }
        return _customBarcodeMap;
    })();
    return _fetchPromise;
}

function findProductById(pos, id) {
    try {
        const m = pos.models?.['product.product'];
        if (!m) return null;
        if (typeof m.getBy === 'function') return m.getBy('id', id) || null;
        if (typeof m.get   === 'function') return m.get(id) || null;
        if (m.records) return m.records[id]
            || Object.values(m.records).find(p => p.id === id) || null;
    } catch(e) {}
    return null;
}

function showNotification(screen, msg) {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) svc.add(msg, { type: 'success' });
        else if (screen.notification) screen.notification.add(msg, { type: 'success' });
    } catch(e) {}
}

function getCurrentOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

// Force price on the selected line AFTER adding (safety net)
function forcePriceOnLine(order, unitPrice) {
    const line = order?.get_selected_orderline?.()
              || order?.selected_orderline
              || order?.get_orderlines?.()?.at(-1)
              || order?.orderlines?.at?.(-1)
              || null;
    if (!line) return;
    if (typeof line.set_unit_price === 'function') { line.set_unit_price(unitPrice); return; }
    if (typeof line.setUnitPrice   === 'function') { line.setUnitPrice(unitPrice);   return; }
    if ('price_unit' in line) line.price_unit = unitPrice;
}

patch(ProductScreen.prototype, {

    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? '');
        const barcodeUpper = raw.toUpperCase();

        if (barcodeUpper) {
            const map   = await fetchCustomBarcodeMap();
            const entry = map[barcodeUpper];

            if (entry) {
                const product = findProductById(this.pos, entry.product_id);
                if (!product) {
                    console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS.`);
                    return super._barcodeProductAction(code);
                }

                // Calculate unit price for the line:
                //   total package price ÷ qty  =  unit price per item on the line
                //   POS then shows:  qty  ×  unit_price  =  package_price  ✅
                //
                // entry.price already accounts for the rule:
                //   custom_price > 0 → custom_price (from server)
                //   custom_price = 0 → unit_price × qty (from server)
                const lineUnitPrice = entry.qty > 0
                    ? entry.price / entry.qty
                    : entry.unit_price;

                try {
                    // Pass price_unit directly — Odoo 19 applies it at line creation time
                    this.pos.addLineToCurrentOrder({
                        product_id: product,
                        qty:        entry.qty,
                        price_unit: lineUnitPrice,
                    });

                    // Safety net: if Odoo ignored price_unit, force it on the line
                    await new Promise(r => setTimeout(r, 40));
                    const order = getCurrentOrder(this.pos);
                    forcePriceOnLine(order, lineUnitPrice);

                } catch (err) {
                    console.error('[CustomBarcode] Error:', err);
                    return super._barcodeProductAction(code);
                }

                const symbol = this.pos.currency?.symbol ?? '₹';
                showNotification(this,
                    `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${entry.price.toFixed(2)}`
                );
                this.numberBuffer?.reset?.();
                return;
            }
        }

        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ Loaded — package barcode scanning with price active.');
