/**
 * TRACE ACTUAL METHOD CALLS
 *
 * Let's hook into posmodel and track EVERY method call to see
 * which ones are actually invoked when user clicks payment buttons
 */

console.clear();
console.log("🔍 TRACING METHOD CALLS\n");

// Create a proxy to intercept all method calls
const originalModel = window.posmodel;
const methodTracer = new Proxy(originalModel, {
    get(target, prop) {
        const value = target[prop];

        // If it's a function, wrap it to trace calls
        if (typeof value === 'function') {
            return function(...args) {
                console.log(`📞 METHOD CALLED: ${String(prop)}()`);
                console.log(`   Args:`, args);

                // Call original method
                return value.apply(target, args);
            };
        }

        return value;
    }
});

// Replace posmodel with traced version
window.posmodel = methodTracer;

console.log("✅ Method tracer activated!");
console.log("\n📝 NOW:");
console.log("1. Create order with price BELOW cost (₹20, cost ₹100)");
console.log("2. Click Cash KDTY button");
console.log("3. Watch console for method calls");
console.log("4. Share the methods you see!\n");

// Also create a manual method logger
window.logPosMethods = function() {
    console.log("\n=== ALL POSMODEL METHODS ===\n");

    const methods = [];
    for (let key of Object.keys(originalModel)) {
        if (typeof originalModel[key] === 'function') {
            methods.push(key);
        }
    }

    // Group by category
    const payMethods = methods.filter(m => m.toLowerCase().includes('pay'));
    const orderMethods = methods.filter(m => m.toLowerCase().includes('order'));
    const validMethods = methods.filter(m => m.toLowerCase().includes('valid'));

    console.log("Payment methods:");
    payMethods.forEach(m => console.log(`  - ${m}()`));

    console.log("\nOrder methods:");
    orderMethods.forEach(m => console.log(`  - ${m}()`));

    console.log("\nValidation methods:");
    validMethods.forEach(m => console.log(`  - ${m}()`));

    console.log("\nAll methods:");
    methods.forEach(m => console.log(`  - ${m}()`));
};

console.log("💡 Or run: logPosMethods()");