/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { Navbar } from "@point_of_sale/app/components/navbar/navbar";
import { useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

// ─── Navbar patch: inline customer search in the top bar ─────────────────────

patch(Navbar.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.cashCustomerInput = useRef("cashCustomerInput");
        this.cashCustomerDropdown = useRef("cashCustomerDropdown");
        this._searchTimeout = null;
        this._selectedPartner = null;
    },

    _getCashCustomerId() {
        const raw = this.pos.config.cash_customer_id;
        return Array.isArray(raw) ? raw[0] : (raw?.id || raw || 0);
    },

    async _getCashCustomerName() {
        const id = this._getCashCustomerId();
        if (!id) return "CASH CUSTOMER";
        try {
            const rows = await this.orm.read("res.partner", [id], ["name"]);
            return rows?.[0]?.name || "CASH CUSTOMER";
        } catch (_e) { return "CASH CUSTOMER"; }
    },

    _showDropdown(items) {
        const dd = this.cashCustomerDropdown.el;
        if (!dd) return;
        dd.innerHTML = "";
        if (!items.length) { dd.style.display = "none"; return; }
        items.forEach(item => {
            const el = document.createElement("div");
            el.style.cssText = "padding:10px 14px;cursor:pointer;border-bottom:1px solid #f5f5f5;font-size:13px;";
            el.innerHTML = `<strong>${item.name}</strong>${item.phone ? ` <span style="color:#999;font-size:12px;"> · ${item.phone}</span>` : ""}`;
            el.onmousedown = (e) => {
                e.preventDefault(); // prevent blur firing before click
                this._selectedPartner = item;
                this.cashCustomerInput.el.value = item.name;
                dd.style.display = "none";
                this._confirmSelection();
            };
            el.onmouseenter = () => el.style.background = "#f5f0ff";
            el.onmouseleave = () => el.style.background = "#fff";
            dd.appendChild(el);
        });

        // Add "Create new" option at bottom
        const createEl = document.createElement("div");
        createEl.style.cssText = "padding:10px 14px;cursor:pointer;font-size:13px;color:#714B67;font-weight:500;border-top:1px solid #eee;";
        createEl.textContent = `+ Create new customer`;
        createEl.onmousedown = (e) => {
            e.preventDefault();
            this._selectedPartner = null;
            dd.style.display = "none";
            this._createNewCustomer();
        };
        dd.appendChild(createEl);
        dd.style.display = "block";
    },

    async onCashCustomerInput() {
        const cashCustomerId = this._getCashCustomerId();
        if (!cashCustomerId) return;

        const val = this.cashCustomerInput.el?.value?.trim();
        this._selectedPartner = null;
        clearTimeout(this._searchTimeout);

        if (!val) {
            this.cashCustomerDropdown.el.style.display = "none";
            return;
        }

        this._searchTimeout = setTimeout(async () => {
            try {
                const found = await this.orm.searchRead(
                    "res.partner",
                    ["|", ["name", "ilike", val], ["phone", "ilike", val],
                     ["customer_rank", ">", 0]],
                    ["name", "phone"],
                    { limit: 6 }
                );
                this._showDropdown(found);
            } catch (_e) {}
        }, 300);
    },

    async onCashCustomerKeydown(ev) {
        const cashCustomerId = this._getCashCustomerId();
        if (!cashCustomerId) return;

        if (ev.key === "Enter") {
            ev.preventDefault();
            clearTimeout(this._searchTimeout);
            this.cashCustomerDropdown.el.style.display = "none";
            if (this._selectedPartner) {
                await this._confirmSelection();
            } else {
                await this._createNewCustomer();
            }
        } else if (ev.key === "Escape") {
            this.cashCustomerDropdown.el.style.display = "none";
            this.cashCustomerInput.el.value = "";
        }
    },

    onCashCustomerBlur() {
        // Delay so mousedown on dropdown fires first
        setTimeout(() => {
            if (this.cashCustomerDropdown.el) {
                this.cashCustomerDropdown.el.style.display = "none";
            }
        }, 200);
    },

    async _confirmSelection() {
        const partner = this._selectedPartner;
        if (!partner) return;
        try {
            await this.pos.data.read("res.partner", [partner.id]);
            const localPartner = this.pos.models["res.partner"].get(partner.id);
            if (localPartner) {
                this.pos.setPartnerToCurrentOrder(localPartner);
                this.notification.add(_t("Customer set: %s", partner.name), { type: "success" });
            }
        } catch (err) {
            this.notification.add(_t("Error: %s", err.message), { type: "danger" });
        }
        this.cashCustomerInput.el.value = "";
        this._selectedPartner = null;
    },

    async _createNewCustomer() {
        const cashCustomerId = this._getCashCustomerId();
        if (!cashCustomerId) return;

        const val = this.cashCustomerInput.el?.value?.trim();
        if (!val) return;

        const cashCustomerName = await this._getCashCustomerName();

        try {
            const result = await this.orm.create("res.partner", [{
                name: val,
                parent_id: cashCustomerId,
                type: "contact",
                customer_rank: 1,
            }]);
            const newPartnerId = Array.isArray(result) ? result[0] : result;
            await this.pos.data.read("res.partner", [newPartnerId]);
            const newPartner = this.pos.models["res.partner"].get(newPartnerId);
            if (newPartner) {
                this.pos.setPartnerToCurrentOrder(newPartner);
                this.notification.add(
                    _t("'%s' created under %s", val, cashCustomerName),
                    { type: "success" }
                );
            }
        } catch (err) {
            this.notification.add(_t("Failed: %s", err.message), { type: "danger" });
        }
        this.cashCustomerInput.el.value = "";
        this._selectedPartner = null;
    },
});

// ─── PartnerList patch: keep the Create button working too ───────────────────

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
            if (rows?.length) cashCustomerName = rows[0].name;
        } catch (_e) {}

        await this._showCashCustomerDialog(cashCustomerId, cashCustomerName);
    },

    async _showCashCustomerDialog(cashCustomerId, cashCustomerName) {
        return new Promise((resolve) => {
            const overlay = document.createElement("div");
            overlay.style.cssText = `
                position:fixed;top:0;left:0;width:100%;height:100%;
                background:rgba(0,0,0,0.5);z-index:99999;
                display:flex;align-items:center;justify-content:center;
            `;
            overlay.innerHTML = `
                <div style="background:#fff;border-radius:8px;padding:24px;width:420px;max-width:90vw;box-shadow:0 4px 20px rgba(0,0,0,0.3);">
                    <h5 style="margin:0 0 4px 0;font-size:16px;font-weight:600;color:#333;">New Customer</h5>
                    <p style="margin:0 0 16px 0;font-size:13px;color:#666;">Under <strong>${cashCustomerName}</strong></p>
                    <label style="font-size:13px;font-weight:500;color:#555;display:block;margin-bottom:6px;">Name or Phone Number</label>
                    <input id="ccd-input" type="text" placeholder="Type to search or create..."
                        style="width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #ccc;border-radius:6px;font-size:14px;outline:none;"/>
                    <div id="ccd-results" style="display:none;border:1px solid #ddd;border-top:none;border-radius:0 0 6px 6px;max-height:180px;overflow-y:auto;background:#fff;"></div>
                    <div id="ccd-hint" style="font-size:12px;color:#888;margin-top:8px;min-height:18px;"></div>
                    <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px;">
                        <button id="ccd-cancel" style="padding:8px 20px;border:1px solid #ccc;border-radius:6px;background:#fff;cursor:pointer;font-size:14px;">Cancel</button>
                        <button id="ccd-ok" style="padding:8px 20px;border:none;border-radius:6px;background:#714B67;color:#fff;cursor:pointer;font-size:14px;font-weight:500;">OK</button>
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

            const close = () => { document.body.removeChild(overlay); resolve(); };

            const showResults = (partners) => {
                results.innerHTML = "";
                if (!partners.length) { results.style.display = "none"; return; }
                partners.forEach(p => {
                    const item = document.createElement("div");
                    item.style.cssText = "padding:10px 12px;cursor:pointer;border-bottom:1px solid #f0f0f0;font-size:13px;";
                    item.innerHTML = `<strong>${p.name}</strong>${p.phone ? ` <span style="color:#888;font-size:12px;">· ${p.phone}</span>` : ""}`;
                    item.onmouseenter = () => item.style.background = "#f5f0ff";
                    item.onmouseleave = () => item.style.background = "#fff";
                    item.onclick = () => {
                        selectedPartner = p;
                        input.value = p.name;
                        results.style.display = "none";
                        hint.textContent = `✓ Will select existing: ${p.name}`;
                        hint.style.color = "#28a745";
                    };
                    results.appendChild(item);
                });
                results.style.display = "block";
            };

            input.addEventListener("input", () => {
                selectedPartner = null;
                hint.textContent = "";
                const val = input.value.trim();
                clearTimeout(searchTimeout);
                if (!val) { results.style.display = "none"; return; }
                hint.textContent = "Searching...";
                searchTimeout = setTimeout(async () => {
                    try {
                        const found = await this.orm.searchRead(
                            "res.partner",
                            ["|", ["name", "ilike", val], ["phone", "ilike", val], ["customer_rank", ">", 0]],
                            ["name", "phone"], { limit: 6 }
                        );
                        showResults(found);
                        hint.textContent = found.length
                            ? `${found.length} match(es) — select or click OK to create new`
                            : `No match — OK will create "${val}" under ${cashCustomerName}`;
                        hint.style.color = "#888";
                    } catch (_e) { hint.textContent = ""; results.style.display = "none"; }
                }, 300);
            });

            okBtn.onclick = async () => {
                const val = input.value.trim();
                if (!val) { hint.textContent = "Please enter a name or phone number."; hint.style.color = "#dc3545"; return; }
                if (selectedPartner) {
                    try {
                        await this.pos.data.read("res.partner", [selectedPartner.id]);
                        const partner = this.pos.models["res.partner"].get(selectedPartner.id);
                        if (partner) this.clickPartner(partner);
                        this.notification.add(_t("Selected: %s", selectedPartner.name), { type: "success" });
                    } catch (err) { this.notification.add(_t("Error: %s", err.message), { type: "danger" }); }
                    close(); return;
                }
                try {
                    okBtn.disabled = true; okBtn.textContent = "Creating...";
                    const result = await this.orm.create("res.partner", [{ name: val, parent_id: cashCustomerId, type: "contact", customer_rank: 1 }]);
                    const newPartnerId = Array.isArray(result) ? result[0] : result;
                    await this.pos.data.read("res.partner", [newPartnerId]);
                    const newPartner = this.pos.models["res.partner"].get(newPartnerId);
                    if (newPartner) this.clickPartner(newPartner);
                    this.notification.add(_t("'%s' created under %s", val, cashCustomerName), { type: "success" });
                    close();
                } catch (err) {
                    okBtn.disabled = false; okBtn.textContent = "OK";
                    hint.textContent = `Error: ${err.message}`; hint.style.color = "#dc3545";
                }
            };
            cancelBtn.onclick = close;
            overlay.onclick = (e) => { if (e.target === overlay) close(); };
            setTimeout(() => input.focus(), 50);
        });
    },
});