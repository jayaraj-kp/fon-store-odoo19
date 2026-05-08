/** @odoo-module **/

import { ProductScreen } from '@point_of_sale/app/screens/product_screen/product_screen';
import { patch } from '@web/core/utils/patch';

/**
 * Patch ProductScreen to remove internal reference codes from product display
 * This removes the [CODE] prefix shown in POS product lists
 */
patch(ProductScreen.prototype, {
    getProductDisplayName(product) {
        // Return only the product name without the internal reference code
        return product.display_name || product.name;
    },
});

/**
 * Alternative: If needed for OrderSummary or other POS components
 */
import { OrderSummary } from '@point_of_sale/app/screens/payment_screen/order_summary';

patch(OrderSummary.prototype, {
    getProductName(product) {
        // Return only the product name
        return product.display_name || product.name;
    },
});
