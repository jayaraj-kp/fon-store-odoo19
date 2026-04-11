/**
 * DIAGNOSTIC: Check if sale_price_block JavaScript is loaded
 */

console.clear();
console.log("=== PRICE BLOCK DIAGNOSTIC ===\n");

// Check 1: Is the module loaded?
console.log("1. Checking if module loaded...");
if (window.__pb_loaded) {
    console.log("✅ Module was loaded");
} else {
    console.log("❌ Module NOT loaded - check console for errors");
}

// Check 2: Can we access the order?
console.log("\n2. Checking order access...");
try {
    const order = window.posmodel?.pendingOrder;
    if (order) {
        console.log("✅ Can access order:", order.name);
        console.log("   Order lines:", order.lines?.length || 0);
    } else {
        console.log("❌ Cannot access pendingOrder");
    }
} catch (e) {
    console.log("❌ Error:", e.message);
}

// Check 3: Can we check prices?
console.log("\n3. Checking price logic...");
try {
    const order = window.posmodel?.pendingOrder;
    if (order && order.lines && order.lines.length > 0) {
        const line = order.lines[0];
        const product = line.product_id;
        const salePrice = line.price_unit;
        const costPrice = product?.standard_price || 0;

        console.log("✅ First product:");
        console.log(`   Name: ${product?.display_name}`);
        console.log(`   Sale: ₹${salePrice}`);
        console.log(`   Cost: ₹${costPrice}`);
        console.log(`   Below cost? ${salePrice < costPrice ? 'YES ❌' : 'NO ✅'}`);
    }
} catch (e) {
    console.log("❌ Error checking prices:", e.message);
}

// Check 4: Test the validation function directly
console.log("\n4. Testing validation function...");
try {
    const order = window.posmodel?.pendingOrder;

    let hasBelowCost = false;
    if (order && order.lines) {
        for (const line of order.lines) {
            const cost = line.product_id?.standard_price || 0;
            const sale = line.price_unit || 0;
            if (sale < cost) {
                hasBelowCost = true;
                console.log(`✅ Found below-cost: ${line.product_id?.display_name} (₹${sale} < ₹${cost})`);
            }
        }
    }

    if (!hasBelowCost) {
        console.log("✅ All prices are valid (no below-cost items)");
    }
} catch (e) {
    console.log("❌ Error in validation:", e.message);
}

// Check 5: Check PaymentScreen patching
console.log("\n5. Checking PaymentScreen patch...");
try {
    const PaymentScreen = window.PaymentScreen;
    if (PaymentScreen) {
        console.log("✅ PaymentScreen found");

        // Check if our methods exist
        const proto = PaymentScreen.prototype;
        if (proto.validateOrder) {
            console.log("✅ validateOrder method exists");
        }
        if (proto.validateOrderFast) {
            console.log("✅ validateOrderFast method exists");
        }
        if (proto.addPayment) {
            console.log("✅ addPayment method exists");
        }
    } else {
        console.log("❌ PaymentScreen not found in window");
    }
} catch (e) {
    console.log("❌ Error:", e.message);
}

// Check 6: Look at what methods PaymentScreen actually has
console.log("\n6. PaymentScreen available methods:");
try {
    const PaymentScreen = window.PaymentScreen;
    if (PaymentScreen) {
        const methods = Object.getOwnPropertyNames(PaymentScreen.prototype);
        const payMethods = methods.filter(m =>
            m.toLowerCase().includes('pay') ||
            m.toLowerCase().includes('validate') ||
            m.toLowerCase().includes('add')
        );

        if (payMethods.length > 0) {
            payMethods.forEach(m => console.log(`  - ${m}`));
        } else {
            console.log("  (None matching 'pay', 'validate', 'add')");
        }
    }
} catch (e) {
    console.log("❌ Error:", e.message);
}

// Check 7: Check if there are any JavaScript errors in console
console.log("\n7. Check browser console for red errors ⚠️");
console.log("   If you see red errors, screenshot them!");

console.log("\n=== END DIAGNOSTIC ===\n");
console.log("Share this output with exact results!");