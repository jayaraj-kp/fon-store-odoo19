/**
 * SIMPLE TEST - Just check if we can access pendingOrder and its data
 */

console.clear();
console.log("🔍 TESTING pendingOrder ACCESS\n");

// Test 1: Does pendingOrder exist?
try {
    const order = posmodel.pendingOrder;
    console.log("✅ posmodel.pendingOrder exists");
    console.log("   Order object:", order);
} catch (e) {
    console.log("❌ Error accessing pendingOrder:", e.message);
}

// Test 2: Can we access lines?
try {
    const lines = posmodel.pendingOrder.lines;
    console.log("\n✅ posmodel.pendingOrder.lines exists");
    console.log("   Number of lines:", lines.length);

    if (lines.length > 0) {
        const firstLine = lines[0];
        console.log("   First line:", firstLine);
    }
} catch (e) {
    console.log("\n❌ Error accessing lines:", e.message);
}

// Test 3: Can we access product info?
try {
    const firstLine = posmodel.pendingOrder.lines[0];
    const product = firstLine.product_id;
    const salePrice = firstLine.price_unit;
    const costPrice = product.standard_price;

    console.log("\n✅ Can access product info:");
    console.log("   Product:", product.display_name);
    console.log("   Sale Price:", salePrice);
    console.log("   Cost Price:", costPrice);
    console.log("   Is valid (>= cost)?", salePrice >= costPrice ? "YES ✅" : "NO ❌");
} catch (e) {
    console.log("\n❌ Error accessing product info:", e.message);
}

// Test 4: Test the validation logic
console.log("\n=== VALIDATION TEST ===");

try {
    const order = posmodel.pendingOrder;
    const lines = order.lines;

    let belowCostCount = 0;
    const belowCostItems = [];

    lines.forEach((line, index) => {
        const salePrice = line.price_unit;
        const costPrice = line.product_id.standard_price;

        if (salePrice < costPrice) {
            belowCostCount++;
            belowCostItems.push({
                name: line.product_id.display_name,
                sale: salePrice,
                cost: costPrice
            });
        }
    });

    console.log(`Items below cost: ${belowCostCount}`);

    if (belowCostCount > 0) {
        console.log("❌ ORDER IS INVALID - Items below cost:");
        belowCostItems.forEach(item => {
            console.log(`  • ${item.name}: Sale ₹${item.sale} < Cost ₹${item.cost}`);
        });
    } else {
        console.log("✅ ORDER IS VALID - All prices are OK");
    }

} catch (e) {
    console.log("❌ Error in validation test:", e.message);
}

console.log("\n=== SUMMARY ===");
console.log("If everything above shows ✅, then the data is accessible!");
console.log("If you see ❌ errors, that's the issue we need to fix.");