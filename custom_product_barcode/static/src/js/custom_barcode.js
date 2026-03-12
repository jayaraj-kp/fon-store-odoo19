/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE
 *
 * Approach: Read barcode2/barcode3 + custom_qty/price from the product object
 * that POS already loaded (injected by pos_session.py). Build a local lookup
 * map on setup. Intercept _barcodeProductAction for scanner and keydown for
 * typed search. Use a single entry point with a hard dedup lock.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { onMounted, onWillUnmount } from "@odoo/owl";

console.log('[CustomBarcode] ✅ Module loading...');

// ── Build barcode map from POS product data ───────────────────────────────────
// Called once after POS is ready. Returns Map<BARCODE_UPPER → {product, qty, price}>
function buildBarcodeMap(pos) {
    const map = new Map();
    try {
        const model = pos.models?.['product.product'];
        if (!model) { console.warn('[CustomBarcode] product.product model not found'); return map; }

        // Collect all product records
        let products = [];
        if (typeof model.getAll === 'function') products = model.getAll();
        else if (model.records) products = Object.values(model.records);
        else if (typeof model.get === 'function') {
            // iterate known ids — fallback
            products = [];
        }

        for (const p of products) {
            if (p.barcode2 && p.custom_qty1) {
                const price = (p.custom_price1 > 0) ? p.custom_price1 : p.lst_price;
                map.set(p.barcode2.toUpperCase(), { product: p, qty: p.custom_qty1, price });
            }
            if (p.barcode3 && p.custom_qty2) {
                const price = (p.custom_price2 > 0) ? p.custom_price2 : p.lst_price;
                map.set(p.barcode3.toUpperCase(), { product: p, qty: p.custom_qty2, price });
            }
        }
        console.log(`[CustomBarcode] ✅ Built map with ${map.size} custom barcode(s):`, [...map.keys()]);
    } catch(e) {
        console.error('[CustomBarcode] buildBarcodeMap error:', e);
    }
    return map;
}

// ── Dedup: one barcode handled max once per 1500ms ────────────────────────────
const _seen = new Map();
function isDuplicate(key) {
    const now = Date.now();
    if (_seen.has(key) && (now - _seen.get(key)) < 1500) return true;
    _seen.set(key, now);
    return false;
}

// ── Get current order ─────────────────────────────────────────────────────────
function getOrder(pos) {
    return pos.get_order?.() || pos.selectedOrder || pos.currentOrder || null;
}

// ── Get last orderline ────────────────────────────────────────────────────────
function getLastLine(order) {
    const lines = order?.get_orderlines?.() || order?.orderlines || [];
    const arr = Array.isArray(lines) ? lines : [...lines];
    return arr.at(-1) || null;
}

// ── Show notification ─────────────────────────────────────────────────────────
function notify(screen, msg) {
    try { screen.env.services.notification.add(msg, { type: 'success' }); } catch(e) {}
}

// ── Core handler ─────────────────────────────────────────────────────────────
async function handleBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const key = rawBarcode.trim().toUpperCase();
    if (isDuplicate(key)) return true; // swallow duplicate silently

    const entry = screen._customBarcodeMap?.get(key);
    if (!entry) {
        _seen.delete(key); // not our barcode, let Odoo handle it normally
        return false;
    }

    console.log(`[CustomBarcode] Handling: ${entry.product.display_name}  qty=${entry.qty}  price=${entry.price}`);

    try {
        const order = getOrder(screen.pos);
        if (!order) throw new Error('No active order');

        // Add line — use merge:false so we always get a fresh line we can control
        screen.pos.addLineToCurrentOrder(
            { product_id: entry.product },
            { merge: false }
        );

        // Immediately grab the new line and set values
        const line = getLastLine(order);
        if (!line) throw new Error('No line after addLineToCurrentOrder');

        // Set qty first
        if      (typeof line.set_quantity  === 'function') line.set_quantity(entry.qty);
        else if (typeof line.setQuantity   === 'function') line.setQuantity(entry.qty);
        else    line.qty = entry.qty;

        // Set price
        if      (typeof line.set_unit_price === 'function') line.set_unit_price(entry.price);
        else if (typeof line.setUnitPrice   === 'function') line.setUnitPrice(entry.price);
        else    line.price_unit = entry.price;

        // Mark as manually set so pricelist won't overwrite
        line.price_manually_set = true;

        console.log(`[CustomBarcode] Line set → qty=${line.qty ?? line.quantity}  price_unit=${line.price_unit}`);

        // Safety re-apply after Odoo's async hooks (pricelist RPC etc.)
        await new Promise(r => setTimeout(r, 80));
        if (Math.abs((line.price_unit ?? 0) - entry.price) > 0.01) {
            console.log(`[CustomBarcode] Price was reset to ${line.price_unit}, re-applying ${entry.price}`);
            if (typeof line.set_unit_price === 'function') line.set_unit_price(entry.price);
            else line.price_unit = entry.price;
            line.price_manually_set = true;
        }
        if (Math.abs((line.qty ?? line.quantity ?? 0) - entry.qty) > 0.01) {
            if (typeof line.set_quantity === 'function') line.set_quantity(entry.qty);
            else line.qty = entry.qty;
        }

        await new Promise(r => setTimeout(r, 300));
        if (Math.abs((line.price_unit ?? 0) - entry.price) > 0.01) {
            console.log(`[CustomBarcode] Price reset again at 380ms, forcing ${entry.price}`);
            if (typeof line.set_unit_price === 'function') line.set_unit_price(entry.price);
            else line.price_unit = entry.price;
            line.price_manually_set = true;
        }

    } catch(err) {
        console.error('[CustomBarcode] Error:', err);
        return false;
    }

    const sym = screen.pos.currency?.symbol ?? '₹';
    notify(screen,
        `${entry.product.display_name} × ${entry.qty} @ ${sym}${entry.price.toFixed(2)} = ${sym}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input helpers ──────────────────────────────────────────────────────
const SELECTORS = [
    'input[placeholder*="earch"]',
    '.search-bar input',
    '.pos-search-bar input',
    '.product-screen input[type="text"]',
];
function findInput() {
    for (const s of SELECTORS) { const el = document.querySelector(s); if (el) return el; }
    return null;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    setup() {
        super.setup();

        // Build map once POS data is available
        this._customBarcodeMap = buildBarcodeMap(this.pos);
        if (this._customBarcodeMap.size === 0) {
            // Retry after a tick in case products load asynchronously
            setTimeout(() => {
                this._customBarcodeMap = buildBarcodeMap(this.pos);
            }, 1000);
        }

        let _input    = null;
        let _handler  = null;
        let _observer = null;

        const attach = (el) => {
            if (!el || el === _input) return;
            if (_input && _handler) _input.removeEventListener('keydown', _handler, true);
            _input = el;
            _handler = async (evt) => {
                if (evt.key !== 'Enter') return;
                const val = el.value?.trim();
                if (!val) return;
                const handled = await handleBarcode(this, val);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    // Clear input
                    try {
                        const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
                        s?.set?.call(el, '');
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                    } catch(e) { el.value = ''; }
                    try { this.updateSearch?.(''); }      catch(e) {}
                    try { if (this.state?.searchWord !== undefined) this.state.searchWord = ''; } catch(e) {}
                }
            };
            _input.addEventListener('keydown', _handler, true);
        };

        onMounted(() => {
            attach(findInput());
            _observer = new MutationObserver(() => {
                const n = findInput();
                if (n && n !== _input) attach(n);
            });
            _observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            if (_input && _handler) _input.removeEventListener('keydown', _handler, true);
            _observer?.disconnect();
        });
    },

    // Physical scanner
    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        if (raw && await handleBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ Patch applied to ProductScreen');