import {registry} from "@web/core/registry";

/** Shared between ReconcileController and ir.actions.client handler */
export const reconcileInlineCreateBus = new EventTarget();

registry.category("actions").add(
    "account_reconcile_oca.reconcile_inline_create_done",
    async (env, action) => {
        const params = action.params || {};
        reconcileInlineCreateBus.dispatchEvent(
            new CustomEvent("inline-create-done", {detail: params})
        );
    }
);
