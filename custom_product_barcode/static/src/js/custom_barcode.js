/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v19)
 *
 * Problem identified: Owl re-renders the search input on every keystroke,
 * replacing the DOM element — so onMounted listener gets detached immediately.
 *
 * Fix: MutationObserver watches for input appearing/changing and re-attaches.
 * Also patches _barcodeProductAction for physical scanner.
 */

import { patch }         from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { onMounted, onWillUnmount } from "@odoo/owl";

// ── Barcode map cache ─────────────────────────────────────────────────────────
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
            console.log(`[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} barcode(s) loaded:`, Object.keys(_customBarcodeMap));
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

function getLastLine(order) {
    return order?.get_selected_orderline?.()
        || order?.selected_orderline
        || order?.get_orderlines?.()?.at(-1)
        || order?.orderlines?.at?.(-1) || null;
}

// Set price using the same pattern that successfully sets qty in Odoo 19
function setPriceOnLine(line, price) {
    if (!line) { console.warn('[CustomBarcode] No line to set price on'); return false; }
    console.log('[CustomBarcode] Line price methods:', 
        ['set_unit_price','setUnitPrice','set_price','setPrice','update']
        .filter(m => typeof line[m] === 'function'));
    console.log('[CustomBarcode] Current price_unit:', line.price_unit, '| price:', line.price);
    
    // Method 1: set_unit_price (standard Odoo method, triggers recomputation)
    if (typeof line.set_unit_price === 'function') {
        line.set_unit_price(price);
        console.log('[CustomBarcode] set_unit_price(' + price + ') → price_unit now:', line.price_unit);
        return true;
    }
    // Method 2: update() reactive model method (Odoo 19)
    if (typeof line.update === 'function') {
        line.update({ price_unit: price });
        console.log('[CustomBarcode] update({price_unit:' + price + '})');
        return true;
    }
    // Method 3: direct assignment (last resort)
    if ('price_unit' in line) {
        line.price_unit = price;
        console.log('[CustomBarcode] line.price_unit=' + price);
        return true;
    }
    return false;
}

async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;
    const map   = await fetchCustomBarcodeMap();
    const entry = map[rawBarcode.toUpperCase()];
    if (!entry) return false;

    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS.`);
        return false;
    }

    try {
        // Pass price through options — Odoo 19 addLineToCurrentOrder accepts
        // an options object that gets forwarded to Order._add_product_to_current_order
        screen.pos.addLineToCurrentOrder({
            product_id: product,
            qty:        entry.qty,
        }, {
            price_unit:     entry.price,
            price_extra:    0,
            lst_price:      entry.price,
            price_manually_set: true,
        });

        // Wait for ALL of Odoo's post-add hooks to finish (price resets happen ~50ms after)
        // then forcefully override with our price — this must win the last write
        await new Promise(r => setTimeout(r, 150));
        const order = getCurrentOrder(screen.pos);
        const line  = getLastLine(order);

        if (line) {
            console.log('[CustomBarcode] Before price set — price_unit:', line.price_unit, 'price:', line.price);
            
            // Call set_unit_price which triggers full recomputation chain
            if (typeof line.set_unit_price === 'function') {
                line.set_unit_price(entry.price);
                // Call again after another tick in case Odoo resets it
                await new Promise(r => setTimeout(r, 50));
                line.set_unit_price(entry.price);
            } else if (typeof line.update === 'function') {
                line.update({ price_unit: entry.price, price_manually_set: true });
            } else if ('price_unit' in line) {
                line.price_unit = entry.price;
            }

            console.log('[CustomBarcode] After price set — price_unit:', line.price_unit, 'price:', line.price);
        }

    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    const symbol = screen.pos.currency?.symbol ?? '₹';
    showNotification(screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}`
    );
    screen.numberBuffer?.reset?.();
    return true;
}

// ── Search input selectors to try ─────────────────────────────────────────────
const SEARCH_SELECTORS = [
    'input[placeholder*="earch"]',
    '.search-bar input',
    '.pos-search-bar input',
    '.product-screen input[type="text"]',
    '.pos input[type="text"]',
];

function findSearchInput() {
    for (const sel of SEARCH_SELECTORS) {
        const el = document.querySelector(sel);
        if (el) return el;
    }
    return null;
}

// ── Patch ProductScreen ───────────────────────────────────────────────────────
patch(ProductScreen.prototype, {

    setup() {
        super.setup();
        fetchCustomBarcodeMap().catch(() => {});

        // We use a MutationObserver so we always have the CURRENT input element
        // even after Owl re-renders replace it.
        let _currentInput   = null;
        let _keyHandler     = null;
        let _observer       = null;

        const attachToInput = (input) => {
            if (!input || input === _currentInput) return;
            // Remove old listener
            if (_currentInput && _keyHandler) {
                _currentInput.removeEventListener('keydown', _keyHandler, true);
                console.log('[CustomBarcode] Detached from old input');
            }
            _currentInput = input;
            _keyHandler = async (evt) => {
                if (evt.key !== 'Enter') return;
                const word = input.value?.trim();
                console.log('[CustomBarcode] Search Enter pressed, value:', JSON.stringify(word));
                if (!word) return;

                const handled = await handleCustomBarcode(this, word);
                console.log('[CustomBarcode] handleCustomBarcode result:', handled);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    // Clear search input and internal state
                    try {
                        // Reset native input value
                        const nativeInput = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        );
                        nativeInput?.set?.call(input, '');
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                    } catch(e) { input.value = ''; }
                    try { this.updateSearch?.(''); } catch(e) {}
                    try { if (this.state?.searchWord !== undefined) this.state.searchWord = ''; } catch(e) {}
                }
            };
            input.addEventListener('keydown', _keyHandler, true);
            console.log('[CustomBarcode] ✅ Attached keydown listener to search input');
        };

        onMounted(() => {
            // Initial attach
            const input = findSearchInput();
            if (input) attachToInput(input);

            // MutationObserver: re-attach whenever DOM changes (Owl re-renders)
            _observer = new MutationObserver(() => {
                const newInput = findSearchInput();
                if (newInput && newInput !== _currentInput) {
                    console.log('[CustomBarcode] Input element replaced — re-attaching listener');
                    attachToInput(newInput);
                }
            });
            _observer.observe(document.body, { childList: true, subtree: true });
        });

        onWillUnmount(() => {
            if (_currentInput && _keyHandler) {
                _currentInput.removeEventListener('keydown', _keyHandler, true);
            }
            _observer?.disconnect();
        });
    },

    // ── Physical barcode scanner ──────────────────────────────────────────────
    async _barcodeProductAction(code) {
        const raw = typeof code === 'string'
            ? code : (code?.code ?? code?.base_code ?? code?.value ?? '');
        console.log('[CustomBarcode] _barcodeProductAction called with:', JSON.stringify(raw));
        if (raw && await handleCustomBarcode(this, raw)) return;
        return super._barcodeProductAction(code);
    },
});

console.log('[CustomBarcode] ✅ v19 loaded — MutationObserver search listener active.');
