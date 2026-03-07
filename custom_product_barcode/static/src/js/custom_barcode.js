/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (Final + Package Price)
 *
 * Scan Barcode 2 → adds Package Qty 1 at Package Price 1
 * Scan Barcode 3 → adds Package Qty 2 at Package Price 2
 *
 * Price logic (set on product form):
 *   Package Price > 0 → use that fixed price for the whole package
 *   Package Price = 0 → use unit price × qty (auto-calculated)
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
        if (m.records) return m.records[id] || Object.values(m.records).find(p => p.id === id) || null;
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

// Set a custom price on the last added order line
function setPriceOnLine(order, price) {
    const line = order?.get_selected_orderline?.()
              || order?.selected_orderline
              || order?.get_orderlines?.()?.at(-1)
              || order?.orderlines?.at?.(-1)
              || null;

    if (!line) return;

    // Odoo 19: line.set_unit_price(price)
    if (typeof line.set_unit_price === 'function') {
        line.set_unit_price(price);
        return;
    }
    if (typeof line.setUnitPrice === 'function') {
        line.setUnitPrice(price);
        return;
    }
    // Direct property fallback
    if ('price_unit' in line) line.price_unit = price;
    else if ('unit_price' in line) line.unit_price = price;
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
                    console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS — enable in POS config.`);
                    return super._barcodeProductAction(code);
                }

                try {
                    // Add line with qty using Odoo 19 API
                    this.pos.addLineToCurrentOrder({ product_id: product, qty: entry.qty });

                    // Apply package price on the new line
                    // entry.price is either custom_price or unit_price × qty from server
                    await new Promise(r => setTimeout(r, 30));
                    const order = getCurrentOrder(this.pos);

                    // Package price from server = price for qty units total
                    // We store it as the unit_price on the line so POS shows: qty × price_unit = total
                    // price_unit = total_package_price / qty
                    const lineUnitPrice = entry.qty > 0 ? entry.price / entry.qty : entry.price;
                    setPriceOnLine(order, lineUnitPrice);

                } catch (err) {
                    console.error('[CustomBarcode] Error:', err);
                    return super._barcodeProductAction(code);
                }

                // Format currency for notification
                const symbol = this.pos.currency?.symbol ?? '';
                showNotification(this, `${entry.product_name}  ×  ${entry.qty}  —  ${symbol}${entry.price.toFixed(2)}`);
                this.numberBuffer?.reset?.();
                return;
            }
        }

        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ Loaded — package barcode scanning with custom price active.');
