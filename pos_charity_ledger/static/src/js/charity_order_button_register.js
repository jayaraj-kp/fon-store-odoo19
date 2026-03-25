/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { CharityOrderButton } from "@pos_charity_ledger/js/charity_button";

// Register CharityOrderButton as a known component inside ControlButtons.
// Using patch() ensures OWL's static component map is updated correctly.
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        CharityOrderButton,
    },
});