/**
 * VERIFY pendingOrder STRUCTURE
 *
 * In Odoo 19 POS, the current order is stored in posmodel.pendingOrder
 * NOT get_order() like older versions
 */

console.clear();
console.log("=== VERIFYING pendingOrder ===\n");

// 1. Check if pendingOrder exists
console.log("posmodel.pendingOrder:", posmodel.pendingOrder);
console.log("Type:", typeof posmodel.pendingOrder);

if (posmodel.pendingOrder) {
    const order = posmodel.pendingOrder;

    console.log("\n=== ORDER STRUCTURE ===");
    console.log("Order object:", order);
    console.log("Order keys:", Object.keys(order).slice(0, 30));

    // 2. Look for order lines
    console.log("\n=== LOOKING FOR ORDER LINES ===");

    const lineKeys = Object.keys(order).filter(k =>
        k.toLowerCase().includes('line') ||
        k.toLowerCase().includes('items') ||
        k.toLowerCase().includes('products')
    );

    console.log("Line-related keys:", lineKeys);

    // Try common names
    const possibleLineKeys = ['lines', 'orderLines', 'order_lines', 'items', 'products', 'line_ids'];
    possibleLineKeys.forEach(key => {
        if (key in order) {
            console.log(`\n✅ Found lines at: order.${key}`);
            const lines = order[key];
            console.log(`   Type: ${typeof lines}`);
            console.log(`   Length: ${lines?.length || 'N/A'}`);

            if (lines && lines.length > 0) {
                console.log(`   First line:`, lines[0]);

                // Check if first line has product info
                if (lines[0]) {
                    console.log(`   First line keys:`, Object.keys(lines[0]).slice(0, 20));
                }
            }
        }
    });

    // 3. Check for methods
    console.log("\n=== ORDER METHODS ===");
    const methods = [];
    for (let key of Object.keys(order)) {
        if (typeof order[key] === 'function') {
            methods.push(key);
        }
    }
    console.log("Methods:", methods.slice(0, 20));

    // Look for "get" methods
    const getMethods = methods.filter(m => m.startsWith('get'));
    console.log("'get' methods:", getMethods);

} else {
    console.log("❌ pendingOrder is null/undefined");

    // If no pending order, check if there's a way to create one or get the current one
    console.log("\n=== ALTERNATIVE PATHS ===");

    // Check if order might be accessed differently
    if (posmodel.models?.Order) {
        console.log("✅ posmodel.models.Order exists");
    }

    if (posmodel.mainScreen) {
        console.log("✅ posmodel.mainScreen exists");
        console.log("   Keys:", Object.keys(posmodel.mainScreen).slice(0, 10));
    }
}

console.log("\n\n=== TEST THE PAYMENT VALIDATION ===");

// Now test if we can validate using the correct structure
if (posmodel.pendingOrder?.lines) {
    console.log("✅ Can access order lines!");

    const lines = posmodel.pendingOrder.lines;
    console.log(`   Total lines: ${lines.length}`);

    // Check each line
    lines.forEach((line, i) => {
        console.log(`\n   Line ${i + 1}:`);
        console.log(`     Product:`, line.product_id?.display_name || 'Unknown');

        // Try to get price info
        console.log(`     Keys:`, Object.keys(line).slice(0, 15));
    });

    console.log("\n✅ Successfully accessed order lines!");
    console.log("✅ Can use for validation!");

} else {
    console.log("⚠️ Cannot access order.lines yet");
}