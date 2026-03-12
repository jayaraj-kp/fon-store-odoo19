// ============================================================
// PASTE THIS ENTIRE BLOCK INTO BROWSER CONSOLE ON POS SCREEN
// Then scan/type barcode A6590 and press Enter in search box
// ============================================================

(async () => {

// STEP 1: Check barcode map loaded correctly
console.log("=== STEP 1: Fetching barcode map ===");
const resp = await fetch('/pos/custom_barcode_map', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: {} }),
});
const json = await resp.json();
const barcodes = (json?.result ?? json)?.barcodes ?? {};
console.log("Raw barcode map:", barcodes);
console.log("Keys in map:", Object.keys(barcodes));
console.log("A6590 entry:", barcodes['A6590'] ?? barcodes['a6590'] ?? "NOT FOUND");

// STEP 2: Find POS instance
console.log("\n=== STEP 2: Finding POS instance ===");
let pos = null;
try {
    // Try Owl component tree
    const el = document.querySelector('.pos, .point-of-sale, [owl-class]');
    const keys = el ? Object.keys(el) : [];
    const owlKey = keys.find(k => k.startsWith('__owl__'));
    if (owlKey) {
        let comp = el[owlKey]?.component;
        while (comp) {
            if (comp.pos || comp.env?.pos) { pos = comp.pos || comp.env.pos; break; }
            comp = comp.__owl__?.parent?.component;
        }
    }
} catch(e) { console.warn("Owl search failed:", e); }

// Fallback: search window
if (!pos) {
    for (const k of Object.keys(window)) {
        try {
            if (window[k]?.models?.['product.product']) { pos = window[k]; break; }
        } catch(e) {}
    }
}
console.log("POS found:", !!pos);
if (!pos) { console.error("❌ Cannot find POS instance — stop here"); return; }

// STEP 3: Find product
console.log("\n=== STEP 3: Finding product id from barcode map ===");
const entry = barcodes['A6590'] ?? barcodes['a6590'];
if (!entry) { console.error("❌ Barcode A6590 not in map"); return; }
console.log("Entry:", entry);

const m = pos.models?.['product.product'];
console.log("Product model:", m);
console.log("getBy method:", typeof m?.getBy);
console.log("get method:", typeof m?.get);
console.log("records:", m?.records ? Object.keys(m.records).slice(0,5) : "none");

let product = null;
if (typeof m?.getBy === 'function') product = m.getBy('id', entry.product_id);
if (!product && typeof m?.get === 'function') product = m.get(entry.product_id);
if (!product && m?.records) product = m.records[entry.product_id] || Object.values(m.records).find(p => p.id === entry.product_id);
console.log("Product found:", product?.display_name ?? product?.name ?? product);

// STEP 4: Check current order
console.log("\n=== STEP 4: Current order ===");
const order = pos.get_order?.() || pos.selectedOrder || pos.currentOrder;
console.log("Order:", order?.name ?? order);
const lines = order?.get_orderlines?.() || order?.orderlines || [];
const arr = Array.isArray(lines) ? lines : (lines.toArray?.() ?? [...lines]);
console.log("Lines before:", arr.length);

// STEP 5: Add line and watch what happens
console.log("\n=== STEP 5: Adding line and watching price ===");
if (!product) { console.error("❌ No product — cannot add line"); return; }

pos.addLineToCurrentOrder({ product_id: product }, { price_manually_set: true });

const checkLine = (label) => {
    const ls = order?.get_orderlines?.() || order?.orderlines || [];
    const a  = Array.isArray(ls) ? ls : (ls.toArray?.() ?? [...ls]);
    const line = a.at(-1);
    if (!line) { console.log(label, "NO LINE"); return; }
    console.log(label, {
        qty:              line.qty,
        quantity:         line.quantity,
        price_unit:       line.price_unit,
        lst_price:        line.lst_price,
        price_manually_set: line.price_manually_set,
        // Log ALL own property keys to find what Odoo 19 uses
        ownKeys:          Object.keys(line).filter(k => !k.startsWith('_')).join(', '),
        // Log available methods
        methods: ['set_unit_price','setUnitPrice','set_quantity','setQuantity','update','getUnitPrice','get_unit_price']
                  .filter(fn => typeof line[fn] === 'function').join(', '),
    });
};

checkLine("t=0ms (immediate):");

await new Promise(r => setTimeout(r, 50));
checkLine("t=50ms:");

await new Promise(r => setTimeout(r, 150));
checkLine("t=200ms:");

await new Promise(r => setTimeout(r, 300));
checkLine("t=500ms:");

await new Promise(r => setTimeout(r, 500));
checkLine("t=1000ms:");

await new Promise(r => setTimeout(r, 1000));
checkLine("t=2000ms:");

console.log("\n=== STEP 6: Try setting price NOW on last line ===");
const ls2 = order?.get_orderlines?.() || order?.orderlines || [];
const a2   = Array.isArray(ls2) ? ls2 : (ls2.toArray?.() ?? [...ls2]);
const finalLine = a2.at(-1);
if (finalLine) {
    console.log("Trying set_unit_price(300)...");
    if (typeof finalLine.set_unit_price === 'function') finalLine.set_unit_price(300);
    else finalLine.price_unit = 300;

    await new Promise(r => setTimeout(r, 100));
    console.log("price_unit after manual set:", finalLine.price_unit);

    await new Promise(r => setTimeout(r, 1000));
    console.log("price_unit after 1s (did Odoo reset it?):", finalLine.price_unit);
}

console.log("\n=== DONE — copy ALL output above and share it ===");

})();