/** @odoo-module **/

import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { CharityOrderButton } from "@pos_charity_ledger/js/charity_button";

// Register CharityOrderButton as a known component inside ControlButtons
ControlButtons.components = {
    ...ControlButtons.components,
    CharityOrderButton,
};
