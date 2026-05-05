/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { FieldMany2One } from "@web/views/fields/many2one/many2one_field";

/**
 * Password Dialog Component
 * Shows when user tries to change the POS Operation Type
 */
export class PosOperationTypePasswordDialog extends Component {
    static template = "pos_operation_type_lock.PasswordDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        onConfirm: Function,
    };

    setup() {
        this.state = useState({
            password: "",
            error: "",
            isLoading: false,
        });
        this.orm = useService("orm");
        this.passwordRef = useRef("passwordInput");
    }

    async onConfirm() {
        if (!this.state.password) {
            this.state.error = _t("Please enter the password.");
            return;
        }
        this.state.isLoading = true;
        this.state.error = "";

        try {
            const result = await this.orm.call(
                "pos.operation.type.lock.config",
                "check_and_verify_password",
                [this.state.password]
            );

            if (result.success) {
                this.props.onConfirm();
                this.props.close();
            } else {
                this.state.error = result.message || _t("Incorrect password.");
                this.state.password = "";
            }
        } catch (error) {
            this.state.error = _t("An error occurred. Please try again.");
        } finally {
            this.state.isLoading = false;
        }
    }

    onCancel() {
        this.props.close();
    }

    onKeyDown(ev) {
        if (ev.key === "Enter") {
            this.onConfirm();
        }
    }
}

/**
 * Patch the Many2One field used for picking_type_id in POS config
 * to intercept changes and require password
 */
let _lockStatus = null;

async function getLockStatus(orm) {
    if (_lockStatus === null) {
        try {
            _lockStatus = await orm.call(
                "pos.operation.type.lock.config",
                "is_operation_type_locked",
                []
            );
        } catch (e) {
            _lockStatus = { is_locked: false, has_password: false };
        }
    }
    return _lockStatus;
}

// Register a field component patch for POS config picking_type_id
const posConfigPickingTypePatch = {
    setup() {
        super.setup(...arguments);
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this._unlocked = false;
    },

    async openSearchView() {
        // Only intercept if we're in the pos.config model and picking_type_id field
        const isPickingTypeField = this.props?.name === "picking_type_id";
        const isPosConfigModel = this.props?.record?.resModel === "pos.config";

        if (isPickingTypeField && isPosConfigModel && !this._unlocked) {
            const lockStatus = await getLockStatus(this.orm);

            if (lockStatus.is_locked && lockStatus.has_password) {
                // Show password dialog before allowing change
                await new Promise((resolve) => {
                    this.dialogService.add(PosOperationTypePasswordDialog, {
                        onConfirm: () => {
                            this._unlocked = true;
                            resolve(true);
                            // Call the original openSearchView
                            super.openSearchView();
                        },
                        close: () => {
                            resolve(false);
                        },
                    });
                });
                return;
            }
        }
        super.openSearchView();
    },
};

// We patch FieldMany2One for pos.config picking_type_id
patch(FieldMany2One.prototype, posConfigPickingTypePatch);
