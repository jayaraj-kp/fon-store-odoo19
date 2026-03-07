/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v10)
 *
 * Strategy: Use pos.addProductToCurrentOrder() (the ONLY reliable way in
 * Odoo 19 to add a product and get a reactive UI update), then immediately
 * patch the qty on the new line via the reactive model's own update method.
 *
 * Key insight: Odoo 19 Order lines are reactive objects managed by the
 * model store. We must update qty through the model, not by direct assignment.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Cache ─────────────────────────────────────────────────────────────────────
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
            for (const [k, v] of Object.entries(raw)) {
                _customBarcodeMap[k.toUpperCase()] = v;
            }
            console.log('[CustomBarcode] ✅ Map loaded:', Object.keys(_customBarcodeMap));
        } catch (e) {
            console.error('[CustomBarcode] ❌ Map load failed:', e);
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

// ── Set quantity on an order line using every known Odoo 19 method ────────────
function setLineQty(line, qty) {
    if (!line) { console.warn('[CustomBarcode] No line found to set qty'); return false; }

    // Log what methods are available on the line
    const methods = ['set_quantity','setQuantity','set_qty','update'].filter(m => typeof line[m] === 'function');
    const props   = ['qty','quantity'].filter(p => p in line);
    console.log('[CustomBarcode] Line methods:', methods, '| props:', props, '| current qty:', line.qty ?? line.quantity);

    // Odoo 19: line.set_quantity(qty) — qty as number
    if (typeof line.set_quantity === 'function') {
        line.set_quantity(qty);
        console.log('[CustomBarcode] ✅ set_quantity(' + qty + ') → line qty now:', line.qty ?? line.quantity);
        return true;
    }
    // Odoo 19 alternative name
    if (typeof line.setQuantity === 'function') {
        line.setQuantity(qty);
        console.log('[CustomBarcode] ✅ setQuantity(' + qty + ')');
        return true;
    }
    // Generic update (Odoo 19 reactive model update)
    if (typeof line.update === 'function') {
        line.update({ qty });
        console.log('[CustomBarcode] ✅ update({qty:' + qty + '})');
        return true;
    }
    // Direct property
    if ('qty' in line)      { line.qty      = qty; console.log('[CustomBarcode] ✅ line.qty=' + qty); return true; }
    if ('quantity' in line) { line.quantity = qty; console.log('[CustomBarcode] ✅ line.quantity=' + qty); return true; }

    console.error('[CustomBarcode] ❌ No method found to set qty on line');
    return false;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
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
                    console.warn('[CustomBarcode] Product id=' + entry.product_id + ' not in POS — enable in POS config');
                    return super._barcodeProductAction(code);
                }

                try {
                    // Step 1: Add with qty=1 via the official Odoo 19 API
                    // (quantity option is ignored by Odoo 19 but we still try)
                    await this.pos.addProductToCurrentOrder(product, { quantity: entry.qty });
                    console.log('[CustomBarcode] addProductToCurrentOrder called');

                    // Step 2: Immediately get the selected line and force qty
                    // Use nextTick to let Owl commit the reactive state first
                    await new Promise(r => setTimeout(r, 30));

                    const order = getCurrentOrder(this.pos);
                    console.log('[CustomBarcode] Order:', order?.constructor?.name, '| lines count:', order?.get_orderlines?.()?.length ?? order?.orderlines?.length);

                    const line = order?.get_selected_orderline?.()
                              || order?.selected_orderline
                              || order?.selectedOrderline
                              || order?.get_orderlines?.()?.at(-1)   // last added line
                              || order?.orderlines?.at?.(-1);

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
console.log('[CustomBarcode] ✅ v10 loaded.');
