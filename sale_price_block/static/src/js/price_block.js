/////**
//// * SIMPLE TEST - Just check if we can access pendingOrder and its data
//// */
////
////console.clear();
////console.log("🔍 TESTING pendingOrder ACCESS\n");
////
////// Test 1: Does pendingOrder exist?
////try {
////    const order = posmodel.pendingOrder;
////    console.log("✅ posmodel.pendingOrder exists");
////    console.log("   Order object:", order);
////} catch (e) {
////    console.log("❌ Error accessing pendingOrder:", e.message);
////}
////
////// Test 2: Can we access lines?
////try {
////    const lines = posmodel.pendingOrder.lines;
////    console.log("\n✅ posmodel.pendingOrder.lines exists");
////    console.log("   Number of lines:", lines.length);
////
////    if (lines.length > 0) {
////        const firstLine = lines[0];
////        console.log("   First line:", firstLine);
////    }
////} catch (e) {
////    console.log("\n❌ Error accessing lines:", e.message);
////}
////
////// Test 3: Can we access product info?
////try {
////    const firstLine = posmodel.pendingOrder.lines[0];
////    const product = firstLine.product_id;
////    const salePrice = firstLine.price_unit;
////    const costPrice = product.standard_price;
////
////    console.log("\n✅ Can access product info:");
////    console.log("   Product:", product.display_name);
////    console.log("   Sale Price:", salePrice);
////    console.log("   Cost Price:", costPrice);
////    console.log("   Is valid (>= cost)?", salePrice >= costPrice ? "YES ✅" : "NO ❌");
////} catch (e) {
////    console.log("\n❌ Error accessing product info:", e.message);
////}
////
////// Test 4: Test the validation logic
////console.log("\n=== VALIDATION TEST ===");
////
////try {
////    const order = posmodel.pendingOrder;
////    const lines = order.lines;
////
////    let belowCostCount = 0;
////    const belowCostItems = [];
////
////    lines.forEach((line, index) => {
////        const salePrice = line.price_unit;
////        const costPrice = line.product_id.standard_price;
////
////        if (salePrice < costPrice) {
////            belowCostCount++;
////            belowCostItems.push({
////                name: line.product_id.display_name,
////                sale: salePrice,
////                cost: costPrice
////            });
////        }
////    });
////
////    console.log(`Items below cost: ${belowCostCount}`);
////
////    if (belowCostCount > 0) {
////        console.log("❌ ORDER IS INVALID - Items below cost:");
////        belowCostItems.forEach(item => {
////            console.log(`  • ${item.name}: Sale ₹${item.sale} < Cost ₹${item.cost}`);
////        });
////    } else {
////        console.log("✅ ORDER IS VALID - All prices are OK");
////    }
////
////} catch (e) {
////    console.log("❌ Error in validation test:", e.message);
////}
////
////console.log("\n=== SUMMARY ===");
////console.log("If everything above shows ✅, then the data is accessible!");
////console.log("If you see ❌ errors, that's the issue we need to fix.");
///** @odoo-module **/
//
//import { patch } from "@web/core/utils/patch";
//import { _t } from "@web/core/l10n/translation";
//
///**
// * PERMANENT FIX: Auto-clear error flags when price changes
// *
// * Problem: After validation error, order gets locked (error/invalid flags)
// * Solution: Clear these flags when user updates any line price
// */
//
//// Patch the POS model to monitor price changes
//patch(Object.getPrototypeOf(window.posmodel), {
//    /**
//     * Override the method that handles line changes
//     * Clear error flags when any line is modified
//     */
//    updateLinePrice(line, newPrice) {
//        // Update the price
//        if (line) {
//            line.price_unit = newPrice;
//        }
//
//        // CRITICAL: Clear the error lock flags
//        const order = this.pendingOrder;
//        if (order) {
//            // Clear all error-related properties
//            if ('error' in order) order.error = null;
//            if ('_error' in order) order._error = null;
//            if ('_invalid' in order) order._invalid = null;
//            if ('validation_error' in order) order.validation_error = null;
//            if ('__error__' in order) order.__error__ = null;
//
//            console.log("✅ Cleared order error flags after price change");
//        }
//
//        // Call original method if it exists
//        if (this._super) {
//            return this._super(...arguments);
//        }
//    }
//});
//
///**
// * Alternative: Patch the order line update to clear parent order errors
// */
//patch(Object.getPrototypeOf(window.posmodel), {
//    /**
//     * When any line's price_unit property is set, clear order errors
//     */
//    _handleLineUpdate(line) {
//        const order = this.pendingOrder;
//
//        if (order && line) {
//            // Clear error flags on the order
//            if ('error' in order) {
//                order.error = null;
//                console.log("🟢 Cleared order.error");
//            }
//            if ('_invalid' in order) {
//                order._invalid = null;
//                console.log("🟢 Cleared order._invalid");
//            }
//        }
//
//        return this._super?.(...arguments);
//    }
//});
//
///**
// * CRITICAL FIX: Monitor all payment method calls and clear errors first
// */
//patch(window.posmodel, {
//    /**
//     * Before ANY payment, validate AND clear any stale error flags
//     */
//    async pay() {
//        const order = this.pendingOrder;
//
//        if (order) {
//            // Clear any lingering error flags
//            const errorPropsToClean = [
//                'error', '_error', '_invalid', 'validation_error',
//                '__error__', 'locked', '_locked', 'isLocked',
//                'invalid', 'is_invalid'
//            ];
//
//            errorPropsToClean.forEach(prop => {
//                if (prop in order && order[prop] !== null) {
//                    order[prop] = null;
//                    console.log(`✅ Cleaned ${prop}`);
//                }
//            });
//        }
//
//        // Now proceed with payment
//        return this._super?.(...arguments);
//    }
//});
//
///**
// * BONUS: Add a manual reset function that user/UI can call
// */
//window.resetOrderErrors = function() {
//    const order = window.posmodel?.pendingOrder;
//    if (order) {
//        const props = ['error', '_error', '_invalid', 'validation_error', '__error__', 'locked', '_locked'];
//        props.forEach(p => {
//            if (p in order) order[p] = null;
//        });
//        console.log("✅ Order errors manually reset");
//        return true;
//    }
//    console.log("❌ No order found");
//    return false;
//};
//
//console.log("✅ Price Block Fix Loaded - Auto-clearing error flags on price change");