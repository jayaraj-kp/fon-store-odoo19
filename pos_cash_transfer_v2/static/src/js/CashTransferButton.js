/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { CashTransferPopup } from "./CashTransferPopup";

export class CashTransferButton extends Component {
    static template = "pos_cash_transfer.CashTransferButton";
    static props = {};

    setup() {
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    onClick() {
        this.dialog.add(CashTransferPopup, {});
    }
}
