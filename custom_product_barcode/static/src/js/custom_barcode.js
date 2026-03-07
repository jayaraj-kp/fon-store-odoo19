/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v8)
 * ========================================
 * Fix: Use numberBuffer to pre-set qty BEFORE adding product.
 * This is the native Odoo 19 way — the same path the UI uses when a
 * cashier types a number then clicks a product.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

// ── Module-level cache ────────────────────────────────────────────────────────
let _customBarcodeMap = null;
let _fetchPromise     = null;

// ── Fetch barcode map from Odoo controller ────────────────────────────────────
async function fetchCustomBarcodeMap() {
    if (_customBarcodeMap !== null) return _customBarcodeMap;
    if (_fetchPromise)              return _fetchPromise;

    _fetchPromise = (async () => {
        try {
            const response = await fetch('/pos/custom_barcode_map', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const json = await response.json();
            const raw  = (json?.result ?? json)?.barcodes ?? {};

            _customBarcodeMap = {};
            for (const [barcode, entry] of Object.entries(raw)) {
                _customBarcodeMap[barcode.toUpperCase()] = entry;
            }
            const keys = Object.keys(_customBarcodeMap);
            console.log(`[CustomBarcode] ✅ Map loaded — ${keys.length} barcode(s):`, keys);
        } catch (err) {
            console.error('[CustomBarcode] ❌ Failed to load barcode map:', err);
            _customBarcodeMap = {};
        }
        return _customBarcodeMap;
    })();

    return _fetchPromise;
}

// ── Find product.product in POS store by numeric id ──────────────────────────
function findProductById(pos, productId) {
    try {
        const model = pos.models?.['product.product'];
        if (!model) return null;
        if (typeof model.getBy  === 'function') return model.getBy('id', productId) || null;
        if (typeof model.get    === 'function') return model.get(productId) || null;
        if (model.records) {
            return model.records[productId]
                || Object.values(model.records).find(p => p.id === productId)
                || null;
        }
    } catch (e) { console.error('[CustomBarcode] findProductById:', e); }
    return null;
}

// ── Safe notification ─────────────────────────────────────────────────────────
function showNotification(screen, message) {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) { svc.add(message, { type: 'success' }); return; }
        if (screen.notification) { screen.notification.add(message, { type: 'success' }); }
    } catch (e) {}
}

// ── Get current order ─────────────────────────────────────────────────────────
function getCurrentOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

// ── Force quantity on a line using every known Odoo 19 method ─────────────────
function forceQtyOnLine(line, qty) {
    if (!line) return false;
    const qtyStr = String(qty);

    // Method 1: set_quantity (Odoo 16/17/18/19)
    if (typeof line.set_quantity === 'function') {
        line.set_quantity(qtyStr);
        console.log('[CustomBarcode] set_quantity(' + qty + ') called');
        return true;
    }
    // Method 2: direct reactive property (Odoo 19 reactive model)
    if ('qty' in line) {
        line.qty = qty;
        console.log('[CustomBarcode] line.qty = ' + qty);
        return true;
    }
    if ('quantity' in line) {
        line.quantity = qty;
        console.log('[CustomBarcode] line.quantity = ' + qty);
        return true;
    }
    return false;
}

// ── Main: add product with correct qty ───────────────────────────────────────
async function addProductWithQty(screen, product, qty) {
    const pos = screen.pos;

    // ── STRATEGY 1: numberBuffer pre-load (native Odoo 19 approach) ───────────
    // Odoo POS reads the numberBuffer value when a product is added.
    // By pre-loading it with the package qty, the line is created with the
    // right quantity without needing set_quantity afterward.
    const nb = screen.numberBuffer;
    if (nb) {
        try {
            // Save whatever was in the buffer
            const savedBuffer = nb.get?.() ?? null;

            // Load our qty into the buffer
            if (typeof nb.set === 'function') {
                nb.set(String(qty));
            } else if (typeof nb.sendKey === 'function') {
                nb.reset?.();
                // Type each digit
                for (const ch of String(qty)) nb.sendKey(ch);
            }

            // Now add the product — POS will read the buffer qty
            if (typeof pos.addProductToCurrentOrder === 'function') {
                await pos.addProductToCurrentOrder(product, {});
            } else if (typeof screen.addProductToOrder === 'function') {
                await screen.addProductToOrder(product);
            }

            // Reset buffer to clean state
            nb.reset?.();
            console.log('[CustomBarcode] Strategy 1 (numberBuffer pre-load) used, qty=' + qty);
            return true;
        } catch (e) {
            console.warn('[CustomBarcode] Strategy 1 failed:', e.message);
            nb.reset?.();
        }
    }

    // ── STRATEGY 2: add then set qty on line ──────────────────────────────────
    if (typeof pos.addProductToCurrentOrder === 'function') {
        await pos.addProductToCurrentOrder(product, { quantity: qty });
        await new Promise(r => setTimeout(r, 50)); // wait for reactive update
        const line = getCurrentOrder(pos)?.get_selected_orderline?.()
                  || getCurrentOrder(pos)?.selected_orderline;
        forceQtyOnLine(line, qty);
        console.log('[CustomBarcode] Strategy 2 (add + set) used, qty=' + qty);
        return true;
    }

    // ── STRATEGY 3: legacy order.add_product ─────────────────────────────────
    const order = getCurrentOrder(pos);
    if (order && typeof order.add_product === 'function') {
        order.add_product(product, { quantity: qty });
        console.log('[CustomBarcode] Strategy 3 (legacy add_product) used, qty=' + qty);
        return true;
    }

    return false;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
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

                if (product) {
                    try {
                        await addProductWithQty(this, product, entry.qty);
                    } catch (err) {
                        console.error('[CustomBarcode] add error:', err);
                        return super._barcodeProductAction(code);
                    }
                    showNotification(this, `${entry.product_name}  ×  ${entry.qty}`);
                    this.numberBuffer?.reset?.();
                    return;
                } else {
                    console.warn(
                        `[CustomBarcode] product_id=${entry.product_id} not in POS. ` +
                        `Enable it in this POS configuration.`
                    );
                }
            }
        }

        return super._barcodeProductAction(code);
    },
});

fetchCustomBarcodeMap().catch(() => {});
console.log('[CustomBarcode] ✅ v8 loaded.');
