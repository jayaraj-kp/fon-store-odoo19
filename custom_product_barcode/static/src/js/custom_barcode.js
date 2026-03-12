/** @odoo-module */
/**
 * custom_barcode.js  –  Odoo 19 CE  (v19)
 *
 * Features:
 *  - Scan Barcode 2 / Barcode 3 → adds package qty at package price
 *  - Max Combo Qty enforcement: if max_combo_qty > 0, the barcode is blocked
 *    after it has been scanned that many times in the current bill.
 *  - MutationObserver keeps the search-input listener alive across Owl re-renders.
 *  - Patches _barcodeProductAction for physical scanner.
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
            console.log(
                `[CustomBarcode] ✅ ${Object.keys(_customBarcodeMap).length} barcode(s) loaded:`,
                Object.keys(_customBarcodeMap)
            );
        } catch (e) {
            console.error('[CustomBarcode] Failed to load barcode map:', e);
            _customBarcodeMap = {};
        }
        return _customBarcodeMap;
    })();
    return _fetchPromise;
}

// ── Combo-scan counter (per bill, keyed by barcode uppercase) ─────────────────
// Structure: { [orderId]: { [barcodeUpper]: scanCount } }
const _comboCounts = {};

function getOrderId(pos) {
    const order = getCurrentOrder(pos);
    if (!order) return null;
    return order.uid || order.id || order.name || String(order);
}

function getComboCount(pos, barcodeUpper) {
    const oid = getOrderId(pos);
    if (!oid) return 0;
    return (_comboCounts[oid]?.[barcodeUpper]) ?? 0;
}

function incrementComboCount(pos, barcodeUpper) {
    const oid = getOrderId(pos);
    if (!oid) return;
    if (!_comboCounts[oid]) _comboCounts[oid] = {};
    _comboCounts[oid][barcodeUpper] = ((_comboCounts[oid][barcodeUpper]) ?? 0) + 1;
}

/**
 * Call this when an order is finalised / a new order starts so we don't
 * accumulate memory forever.  Hook is added in setup() below.
 */
function resetComboCountForOrder(orderId) {
    if (orderId && _comboCounts[orderId]) {
        delete _comboCounts[orderId];
        console.log(`[CustomBarcode] Combo counts cleared for order ${orderId}`);
    }
}

// ── POS helpers ───────────────────────────────────────────────────────────────
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

function showNotification(screen, msg, type = 'success') {
    try {
        const svc = screen.env?.services?.notification;
        if (svc) svc.add(msg, { type });
        else if (screen.notification) screen.notification.add(msg, { type });
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

// ── Main handler ──────────────────────────────────────────────────────────────
async function handleCustomBarcode(screen, rawBarcode) {
    if (!rawBarcode) return false;

    const map         = await fetchCustomBarcodeMap();
    const barcodeKey  = rawBarcode.toUpperCase();
    const entry       = map[barcodeKey];
    if (!entry) return false;

    // ── Combo limit check ────────────────────────────────────────────────────
    const maxCombo = entry.max_combo_qty ?? 0;   // 0 = unlimited
    if (maxCombo > 0) {
        const scannedSoFar = getComboCount(screen.pos, barcodeKey);
        if (scannedSoFar >= maxCombo) {
            const symbol = screen.pos.currency?.symbol ?? '₹';
            showNotification(
                screen,
                `⛔ "${entry.product_name}" package limit reached! ` +
                `Maximum ${maxCombo} combo scan${maxCombo > 1 ? 's' : ''} per bill.`,
                'danger'
            );
            console.warn(
                `[CustomBarcode] Blocked: ${barcodeKey} — limit ${maxCombo}, already scanned ${scannedSoFar}`
            );
            return true;   // return true so normal barcode handling is also suppressed
        }
    }

    // ── Find product ─────────────────────────────────────────────────────────
    const product = findProductById(screen.pos, entry.product_id);
    if (!product) {
        console.warn(`[CustomBarcode] product_id=${entry.product_id} not in POS.`);
        return false;
    }

    // ── Add line ─────────────────────────────────────────────────────────────
    try {
        screen.pos.addLineToCurrentOrder({
            product_id: product,
            qty:        entry.qty,
        }, {
            price_unit:          entry.price,
            price_extra:         0,
            lst_price:           entry.price,
            price_manually_set:  true,
        });

        // Wait for Odoo's post-add hooks, then forcefully set our price
        await new Promise(r => setTimeout(r, 150));
        const order = getCurrentOrder(screen.pos);
        const line  = getLastLine(order);

        if (line) {
            if (typeof line.set_unit_price === 'function') {
                line.set_unit_price(entry.price);
                await new Promise(r => setTimeout(r, 50));
                line.set_unit_price(entry.price);
            } else if (typeof line.update === 'function') {
                line.update({ price_unit: entry.price, price_manually_set: true });
            } else if ('price_unit' in line) {
                line.price_unit = entry.price;
            }
        }

    } catch (err) {
        console.error('[CustomBarcode] Error adding product:', err);
        return false;
    }

    // ── Increment combo counter only after a successful add ───────────────────
    incrementComboCount(screen.pos, barcodeKey);

    const remaining = maxCombo > 0
        ? ` (${maxCombo - getComboCount(screen.pos, barcodeKey)} left this bill)`
        : '';
    const symbol = screen.pos.currency?.symbol ?? '₹';
    showNotification(
        screen,
        `${entry.product_name}  ×  ${entry.qty}  =  ${symbol}${(entry.qty * entry.price).toFixed(2)}${remaining}`
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

        let _currentInput = null;
        let _keyHandler   = null;
        let _observer     = null;
        let _lastOrderId  = null;

        // Watch for order changes so we can reset combo counts on new bills
        const checkOrderChange = () => {
            const oid = getOrderId(this.pos);
            if (oid && oid !== _lastOrderId) {
                // New order started — reset counts for the OLD order
                if (_lastOrderId) resetComboCountForOrder(_lastOrderId);
                _lastOrderId = oid;
            }
        };

        const attachToInput = (input) => {
            if (!input || input === _currentInput) return;
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

                checkOrderChange();
                const handled = await handleCustomBarcode(this, word);
                console.log('[CustomBarcode] handleCustomBarcode result:', handled);
                if (handled) {
                    evt.preventDefault();
                    evt.stopImmediatePropagation();
                    // Clear search input
                    try {
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
            _lastOrderId = getOrderId(this.pos);
            const input = findSearchInput();
            if (input) attachToInput(input);

            // MutationObserver: re-attach whenever Owl re-renders replace the input
            _observer = new MutationObserver(() => {
                checkOrderChange();
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

console.log('[CustomBarcode] ✅ v19 loaded — MutationObserver + Max Combo Qty enforcement active.');
