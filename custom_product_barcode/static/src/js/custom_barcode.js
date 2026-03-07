/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v12)
 *
 * ROOT CAUSE FOUND:
 * Console showed "[SpecialOffer] ✅ Patched addLineToCurrentOrder"
 * → The Odoo 19 POS method to add a product is pos.addLineToCurrentOrder()
 *   NOT pos.addProductToCurrentOrder() or order.add_product()
 *
 * addLineToCurrentOrder(product, options) signature in Odoo 19:
 *   options.quantity sets the line quantity directly.
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
    return order?.get_selected_orderline?.()
        || order?.selected_orderline
        || order?.selectedOrderline
        || order?.get_orderlines?.()?.at(-1)
        || order?.orderlines?.at?.(-1)
        || null;
}

async function addProductWithQty(pos, product, qty) {
    // ── Method 1: Odoo 19 native — addLineToCurrentOrder ─────────────────────
    if (typeof pos.addLineToCurrentOrder === 'function') {
        pos.addLineToCurrentOrder({ product_id: product, qty: qty });
        console.log('[CustomBarcode] ✅ Method 1: addLineToCurrentOrder(qty=' + qty + ')');
        return true;
    }

    // ── Method 2: addLineToCurrentOrder with different arg shape ──────────────
    // Some Odoo 19 builds accept (product, {quantity})
    if (typeof pos.addLineToCurrentOrder === 'function') {
        pos.addLineToCurrentOrder(product, { quantity: qty });
        console.log('[CustomBarcode] ✅ Method 2: addLineToCurrentOrder(product, {quantity})');
        return true;
    }

    // Log all pos methods for diagnosis
    const posMethods = Object.getOwnPropertyNames(Object.getPrototypeOf(pos))
        .filter(m => /add|order|line|product/i.test(m));
    console.warn('[CustomBarcode] addLineToCurrentOrder not found. pos methods:', posMethods);
    return false;
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

                const added = await addProductWithQty(this.pos, product, entry.qty);

                if (added) {
                    // Verify the line qty was set correctly
                    await new Promise(r => setTimeout(r, 50));
                    const order = getCurrentOrder(this.pos);
                    const line  = getLastLine(order);
                    const actualQty = line?.qty ?? line?.quantity ?? '?';
                    console.log('[CustomBarcode] Line qty after add:', actualQty, '(expected ' + entry.qty + ')');

                    // If qty is still wrong, force it
                    if (line && Number(actualQty) !== entry.qty) {
                        console.warn('[CustomBarcode] qty mismatch — forcing...');
                        if (typeof line.set_quantity === 'function') line.set_quantity(entry.qty);
                        else if (typeof line.update === 'function') line.update({ qty: entry.qty });
                        else if ('qty' in line) line.qty = entry.qty;
                    }

                    showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);
                    this.numberBuffer?.reset?.();
                    return;
                } else {
                    // Fallback: let super handle it (adds with qty=1 at minimum)
                    return super._barcodeProductAction(code);
                }
            }
        }
        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v12 loaded.');
