/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v11)
 *
 * CONFIRMED WORKING: order.add_product() adds the product (v9 proved this).
 * THIS VERSION: adds the product via order.add_product(), then logs every
 * property/method on the line so we can see EXACTLY how to set qty.
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
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            const json = await resp.json();
            const raw  = (json?.result ?? json)?.barcodes ?? {};
            _customBarcodeMap = {};
            for (const [k, v] of Object.entries(raw))
                _customBarcodeMap[k.toUpperCase()] = v;
            console.log('[CustomBarcode] ✅ Map loaded:', Object.keys(_customBarcodeMap));
        } catch (e) {
            console.error('[CustomBarcode] ❌', e);
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

function getLastLine(order) {
    // Try every known way to get the last/selected line in Odoo 17/18/19
    return order?.get_selected_orderline?.()
        || order?.selected_orderline
        || order?.selectedOrderline
        || order?.get_orderlines?.()?.at(-1)
        || order?.orderlines?.at?.(-1)
        || (Array.isArray(order?.orderlines) ? order.orderlines[order.orderlines.length - 1] : null)
        || null;
}

function setLineQty(line, qty) {
    if (!line) { console.error('[CustomBarcode] ❌ No line found!'); return; }

    // ── Deep-inspect the line object ─────────────────────────────────────────
    const allMethods = [];
    const allProps   = [];
    let obj = line;
    const seen = new Set();
    while (obj && obj !== Object.prototype) {
        for (const key of Object.getOwnPropertyNames(obj)) {
            if (seen.has(key)) continue;
            seen.add(key);
            try {
                const val = line[key];
                if (typeof val === 'function') allMethods.push(key);
                else allProps.push(key + '=' + JSON.stringify(val)?.slice(0,30));
            } catch(e) {}
        }
        obj = Object.getPrototypeOf(obj);
    }

    // Filter to qty-related names
    const qtyMethods = allMethods.filter(m => /qty|quant|count|amount/i.test(m));
    const qtyProps   = allProps.filter(p => /qty|quant|count/i.test(p));
    console.log('[CustomBarcode] Line qty-methods:', qtyMethods);
    console.log('[CustomBarcode] Line qty-props:', qtyProps);
    console.log('[CustomBarcode] Line class:', line.constructor?.name);
    console.log('[CustomBarcode] Current qty value:', line.qty ?? line.quantity ?? '(unknown)');

    // ── Try every possible method to set qty ─────────────────────────────────
    if (typeof line.set_quantity === 'function') {
        line.set_quantity(qty);
        console.log('[CustomBarcode] ✅ set_quantity(' + qty + ') result:', line.qty ?? line.quantity);
        return;
    }
    if (typeof line.setQuantity === 'function') {
        line.setQuantity(qty);
        console.log('[CustomBarcode] ✅ setQuantity(' + qty + ')');
        return;
    }
    if (typeof line.set_qty === 'function') {
        line.set_qty(qty);
        console.log('[CustomBarcode] ✅ set_qty(' + qty + ')');
        return;
    }
    if (typeof line.update === 'function') {
        line.update({ qty });
        console.log('[CustomBarcode] ✅ update({qty})');
        return;
    }
    if ('qty' in line) {
        line.qty = qty;
        console.log('[CustomBarcode] ✅ line.qty=' + qty);
        return;
    }
    if ('quantity' in line) {
        line.quantity = qty;
        console.log('[CustomBarcode] ✅ line.quantity=' + qty);
        return;
    }
    console.error('[CustomBarcode] ❌ No method found. All methods:', allMethods.slice(0, 50));
}

patch(ProductScreen.prototype, {

    async _barcodeProductAction(code) {
        const raw = typeof code === 'string' ? code
            : (code?.code ?? code?.base_code ?? code?.value ?? '');
        const barcodeUpper = raw.toUpperCase();

        if (barcodeUpper) {
            const map   = await fetchCustomBarcodeMap();
            const entry = map[barcodeUpper];

            if (entry) {
                const product = findProductById(this.pos, entry.product_id);
                if (!product) {
                    console.warn('[CustomBarcode] product id=' + entry.product_id + ' not in POS');
                    return super._barcodeProductAction(code);
                }

                try {
                    const order = getCurrentOrder(this.pos);
                    if (!order) throw new Error('No active order');

                    // Log order class and add_product signature
                    console.log('[CustomBarcode] Order class:', order.constructor?.name);
                    console.log('[CustomBarcode] order.add_product exists:', typeof order.add_product);
                    console.log('[CustomBarcode] order.addProduct exists:', typeof order.addProduct);

                    // Add the product (confirmed working in v9)
                    if (typeof order.add_product === 'function') {
                        order.add_product(product, { quantity: entry.qty });
                    } else if (typeof order.addProduct === 'function') {
                        order.addProduct(product, { quantity: entry.qty });
                    } else {
                        throw new Error('No add_product method on order');
                    }

                    // Wait for reactivity then set qty
                    await new Promise(r => setTimeout(r, 50));
                    const line = getLastLine(order);
                    setLineQty(line, entry.qty);

                } catch (err) {
                    console.error('[CustomBarcode] Error:', err);
                    return super._barcodeProductAction(code);
                }

                showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);
                this.numberBuffer?.reset?.();
                return;
            }
        }
        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v11 loaded.');
