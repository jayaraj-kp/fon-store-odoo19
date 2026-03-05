/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(PartnerList.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async editPartner(p = false) {
        const raw = this.pos.config.cash_customer_id;
        const cashCustomerId = Array.isArray(raw) ? raw[0] : (raw?.id || raw || 0);

        if (p || !cashCustomerId) {
            return super.editPartner(p);
        }

        let cashCustomerName = "CASH CUSTOMER";
        try {
            const rows = await this.orm.read("res.partner", [cashCustomerId], ["name"]);
            if (rows && rows.length) cashCustomerName = rows[0].name;
        } catch (_e) {}

        // Show smart search dialog
        await this._showCashCustomerDialog(cashCustomerId, cashCustomerName);
    },

    async _showCashCustomerDialog(cashCustomerId, cashCustomerName) {
        return new Promise((resolve) => {
            // Build dialog HTML
            const overlay = document.createElement("div");
            overlay.style.cssText = `
                position:fixed;top:0;left:0;width:100%;height:100%;
                background:rgba(0,0,0,0.5);z-index:99999;
                display:flex;align-items:center;justify-content:center;
            `;

            overlay.innerHTML = `
                <div style="background:#fff;border-radius:8px;padding:24px;width:420px;max-width:90vw;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
                    <h5 style="margin:0 0 4px 0;font-size:16px;font-weight:600;color:#333;">
                        New Customer
                    </h5>
                    <p style="margin:0 0 16px 0;font-size:13px;color:#666;">
                        Under <strong>${cashCustomerName}</strong>
                    </p>

                    <label style="font-size:13px;font-weight:500;color:#555;display:block;margin-bottom:6px;">
                        Name or Phone Number
                    </label>
                    <input id="ccd-input" type="text" placeholder="Type to search or create..."
                        style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #ccc;
                               border-radius:6px;font-size:14px;outline:none;" />

                    <div id="ccd-results" style="display:none;border:1px solid #ddd;border-top:none;
                        border-radius:0 0 6px 6px;max-height:180px;overflow-y:auto;background:#fff;"></div>

                    <div id="ccd-hint" style="font-size:12px;color:#888;margin-top:8px;min-height:18px;"></div>

                    <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;">
                        <button id="ccd-cancel" style="padding:8px 20px;border:1px solid #ccc;
                            border-radius:6px;background:#fff;cursor:pointer;font-size:14px;">
                            Cancel
                        </button>
                        <button id="ccd-ok" style="padding:8px 20px;border:none;
                            border-radius:6px;background:#714B67;color:#fff;cursor:pointer;font-size:14px;font-weight:500;">
                            OK
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(overlay);

            const input = overlay.querySelector("#ccd-input");
            const results = overlay.querySelector("#ccd-results");
            const hint = overlay.querySelector("#ccd-hint");
            const okBtn = overlay.querySelector("#ccd-ok");
            const cancelBtn = overlay.querySelector("#ccd-cancel");

            let selectedPartner = null;
            let searchTimeout = null;

            const close = () => {
                document.body.removeChild(overlay);
                resolve();
            };

            const selectPartner = (partner) => {
                selectedPartner = partner;
                input.value = partner.name;
                results.style.display = "none";
                hint.textContent = `✓ Will select existing customer: ${partner.name}`;
                hint.style.color = "#28a745";
            };

            const showResults = (partners) => {
                results.innerHTML = "";
                if (!partners.length) {
                    results.style.display = "none";
                    return;
                }
                partners.forEach(p => {
                    const item = document.createElement("div");
                    item.style.cssText = "padding:10px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px;";
                    item.innerHTML = `<strong>${p.name}</strong>${p.phone ? ` <span style="color:#888;font-size:12px;">· ${p.phone}</span>` : ""}`;
                    item.onmouseenter = () => item.style.background = "#f5f0ff";
                    item.onmouseleave = () => item.style.background = "#fff";
                    item.onclick = () => selectPartner(p);
                    results.appendChild(item);
                });
                results.style.display = "block";
            };

            input.addEventListener("input", () => {
                selectedPartner = null;
                hint.textContent = "";
                hint.style.color = "#888";
                const val = input.value.trim();

                clearTimeout(searchTimeout);
                if (!val) {
                    results.style.display = "none";
                    return;
                }

                hint.textContent = "Searching...";
                searchTimeout = setTimeout(async () => {
                    try {
                        const found = await this.orm.searchRead(
                            "res.partner",
                            ["|", ["name", "ilike", val], ["phone", "ilike", val],
                             ["customer_rank", ">", 0]],
                            ["name", "phone"],
                            { limit: 6 }
                        );
                        showResults(found);
                        if (found.length) {
                            hint.textContent = `${found.length} match(es) found — select one or click OK to create new`;
                            hint.style.color = "#888";
                        } else {
                            hint.textContent = `No match — click OK to create "${val}" under ${cashCustomerName}`;
                            hint.style.color = "#555";
                        }
                    } catch (_e) {
                        hint.textContent = "";
                        results.style.display = "none";
                    }
                }, 300);
            });

            okBtn.onclick = async () => {
                const val = input.value.trim();
                if (!val) {
                    hint.textContent = "Please enter a name or phone number.";
                    hint.style.color = "#dc3545";
                    return;
                }

                if (selectedPartner) {
                    // Select existing partner
                    try {
                        await this.pos.data.read("res.partner", [selectedPartner.id]);
                        const partner = this.pos.models["res.partner"].get(selectedPartner.id);
                        if (partner) this.clickPartner(partner);
                        this.notification.add(_t("Selected existing customer: %s", selectedPartner.name), { type: "success" });
                    } catch (err) {
                        this.notification.add(_t("Error: %s", err.message), { type: "danger" });
                    }
                    close();
                    return;
                }

                // Create new customer under CASH CUSTOMER
                try {
                    okBtn.disabled = true;
                    okBtn.textContent = "Creating...";
                    const result = await this.orm.create("res.partner", [{
                        name: val,
                        parent_id: cashCustomerId,
                        type: "contact",
                        customer_rank: 1,
                    }]);
                    const newPartnerId = Array.isArray(result) ? result[0] : result;
                    await this.pos.data.read("res.partner", [newPartnerId]);
                    const newPartner = this.pos.models["res.partner"].get(newPartnerId);
                    if (newPartner) this.clickPartner(newPartner);
                    this.notification.add(_t("'%s' created under %s", val, cashCustomerName), { type: "success" });
                    close();
                } catch (err) {
                    okBtn.disabled = false;
                    okBtn.textContent = "OK";
                    hint.textContent = `Error: ${err.message}`;
                    hint.style.color = "#dc3545";
                }
            };

            cancelBtn.onclick = close;
            overlay.onclick = (e) => { if (e.target === overlay) close(); };

            // Focus input
            setTimeout(() => input.focus(), 50);
        });
    },
});