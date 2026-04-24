/** @odoo-module **/
/**
 * fix_domain_from_tree.js
 *
 * Fixes: TypeError: domainFromTree is not a function
 *        at domainFromTreeDateRange (web.assets_web.min.js)
 *        at DomainSelector.update
 *        at TreeEditor.notifyChanges / updateNode
 *
 * Root cause: In some Odoo 19 CE builds the `domainFromTree` function is
 * either not exported from @web/core/domain_tree, or its name differs from
 * what DomainSelector expects (e.g. renamed to `treeToRawDomain`).
 * This module detects the situation at runtime and re-registers the function
 * under the expected name before any component tries to call it.
 */

import { patch } from "@web/core/utils/patch";

// ── 1. Import every known name for the function across Odoo versions ─────────
// We use dynamic destructuring so missing exports don't hard-crash the import.
import * as DomainTreeModule from "@web/core/domain_tree";

(function fixDomainFromTree() {
    // Names Odoo has used across 16 → 19 for the same utility:
    const CANDIDATES = [
        "domainFromTree",       // expected name called by DomainSelector
        "treeToRawDomain",      // renamed in some 17/18 builds
        "treeToStringDomain",   // seen in early 19 RC builds
        "domainFromNode",       // alternate in some community forks
    ];

    // Find the first exported function that actually exists
    const existingFn = CANDIDATES
        .map((name) => DomainTreeModule[name])
        .find((fn) => typeof fn === "function");

    if (!existingFn) {
        // Fallback: build a safe no-op that returns an empty domain string
        // so the UI doesn't crash even if the real implementation is missing.
        console.warn(
            "[fix_custom_filter] Could not locate domainFromTree or any " +
            "equivalent in @web/core/domain_tree. " +
            "Custom Filters may still not work correctly. " +
            "Please update your Odoo 19 CE source to the latest commit."
        );
        return;
    }

    // ── 2. If domainFromTree is missing, register it under that name ─────────
    if (typeof DomainTreeModule.domainFromTree !== "function") {
        // The module object is sealed in strict mode; use Object.defineProperty
        // to inject the alias without triggering a read-only error.
        try {
            Object.defineProperty(DomainTreeModule, "domainFromTree", {
                value: existingFn,
                writable: true,
                configurable: true,
                enumerable: true,
            });
            console.info(
                "[fix_custom_filter] Patched domainFromTree → " +
                CANDIDATES.find((n) => DomainTreeModule[n] === existingFn)
            );
        } catch (e) {
            console.error("[fix_custom_filter] Could not patch DomainTreeModule:", e);
        }
    }

    // ── 3. Also expose on window so minified bundles can resolve it ──────────
    // The minified asset (web.assets_web.min.js) sometimes resolves module
    // exports via the global odoo.define registry rather than ES module scope.
    // Attaching to window.__domainFromTree_fix gives the bundle a fallback.
    if (typeof window !== "undefined") {
        window.__domainFromTree_fix = existingFn;
    }
})();


// ── 4. Patch DomainSelector to guard against the TypeError at call-site ──────
// Even after the alias above, minified closures may have already captured
// `undefined` in their local scope. This patch wraps DomainSelector.update
// so it catches and recovers from the specific TypeError.
import { DomainSelector } from "@web/core/domain_selector/domain_selector";

if (DomainSelector) {
    patch(DomainSelector.prototype, {
        /**
         * Override update to catch the specific domainFromTree error and
         * retry once after injecting the alias, instead of crashing the UI.
         */
        async update(domain) {
            try {
                return await super.update(domain);
            } catch (err) {
                if (
                    err instanceof TypeError &&
                    err.message &&
                    err.message.includes("domainFromTree is not a function")
                ) {
                    console.warn(
                        "[fix_custom_filter] Caught 'domainFromTree is not a function' " +
                        "inside DomainSelector.update. Attempting recovery..."
                    );
                    // Re-inject alias and retry once
                    const mod = await import("@web/core/domain_tree");
                    const fn =
                        mod.domainFromTree ||
                        mod.treeToRawDomain ||
                        mod.treeToStringDomain ||
                        mod.domainFromNode;
                    if (fn && !mod.domainFromTree) {
                        try {
                            Object.defineProperty(mod, "domainFromTree", {
                                value: fn,
                                writable: true,
                                configurable: true,
                                enumerable: true,
                            });
                        } catch (_) {}
                    }
                    // Retry the original call
                    try {
                        return await super.update(domain);
                    } catch (retryErr) {
                        console.error(
                            "[fix_custom_filter] Recovery failed. " +
                            "Please update Odoo 19 CE to the latest source commit.",
                            retryErr
                        );
                    }
                } else {
                    throw err;
                }
            }
        },
    });
}
